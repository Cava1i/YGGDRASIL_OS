from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import pandas as pd
import uuid
import os
import string
import random
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.utils import secure_filename
import queue
import json

class MessageAnnouncer:
    def __init__(self):
        self.listeners = []

    def listen(self):
        q = queue.Queue(maxsize=5)
        self.listeners.append(q)
        return q

    def announce(self, msg):
        for i in reversed(range(len(self.listeners))):
            try:
                self.listeners[i].put_nowait(msg)
            except queue.Full:
                del self.listeners[i]

announcer = MessageAnnouncer()

def generate_task_code(length=8):
    """Generate a unique random code for a task"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

from models import (
    AuditLog,
    InviteCode,
    SystemSetting,
    db,
    User,
    Competition,
    Task,
    Answer,
    Writeup,
    Note,
    WriteupLike,
    NoteLike,
)

app = Flask(__name__)
CORS(app) # Allow frontend to access API

def resolve_database_uri():
    configured_uri = (
        os.environ.get('YGGDRASIL_DATABASE_URI')
        or os.environ.get('CAVALI_DATABASE_URI')
    )
    if configured_uri:
        return configured_uri

    modern_db = os.path.join(app.instance_path, 'yggdrasil_os.db')
    legacy_db = os.path.join(app.instance_path, 'cavali_ctf.db')
    if os.path.exists(legacy_db) and not os.path.exists(modern_db):
        return 'sqlite:///cavali_ctf.db'
    return 'sqlite:///yggdrasil_os.db'

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = resolve_database_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

db.init_app(app)

# Ensure upload folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'wps'), exist_ok=True)

DEFAULT_SETTINGS = {
    'registration_enabled': 'true',
    'default_user_role': 'member',
    'max_upload_mb': '50',
    'session_timeout_hours': '12',
    'allow_member_create_competition': 'true',
    'allow_member_delete_own_items': 'true',
    'system_announcement': '',
}

DEFAULT_ADMIN_USERNAME = os.environ.get('YGGDRASIL_ADMIN_USERNAME') or os.environ.get('CAVALI_ADMIN_USERNAME', 'admin')
DEFAULT_ADMIN_PASSWORD = os.environ.get('YGGDRASIL_ADMIN_PASSWORD') or os.environ.get('CAVALI_ADMIN_PASSWORD', '123456')
LEGACY_DEFAULT_ADMIN_PASSWORDS = ('Dxl123456',)
DEFAULT_INVITE_CODE = os.environ.get('YGGDRASIL_DEFAULT_INVITE_CODE') or os.environ.get('CAVALI_DEFAULT_INVITE_CODE', 'xjxy666')

def ensure_column(table_name, column_name, column_sql):
    columns = db.session.execute(db.text(f'PRAGMA table_info({table_name})')).fetchall()
    if any(row[1] == column_name for row in columns):
        return
    db.session.execute(db.text(f'ALTER TABLE {table_name} ADD COLUMN {column_sql}'))
    db.session.commit()

def ensure_schema():
    db.create_all()
    try:
        ensure_column('task', 'pinned_at', 'pinned_at DATETIME')
        ensure_column('user', 'role', "role VARCHAR(20) NOT NULL DEFAULT 'member'")
        ensure_column('user', 'is_active', 'is_active BOOLEAN NOT NULL DEFAULT 1')
        ensure_column('user', 'last_login_at', 'last_login_at DATETIME')
        ensure_column('user', 'token_expires_at', 'token_expires_at DATETIME')
        ensure_column('competition', 'archived_at', 'archived_at DATETIME')
    except Exception:
        db.session.rollback()
        raise

def get_setting(key, default=None):
    setting = SystemSetting.query.filter_by(key=key).first()
    return setting.value if setting else default

def set_setting(key, value):
    setting = SystemSetting.query.filter_by(key=key).first()
    if not setting:
        setting = SystemSetting(key=key, value=str(value))
        db.session.add(setting)
    else:
        setting.value = str(value)
    return setting

def setting_enabled(key, default=True):
    fallback = 'true' if default else 'false'
    return str(get_setting(key, fallback)).lower() in ('1', 'true', 'yes', 'on')

def int_setting(key, default, min_value=None, max_value=None):
    try:
        value = int(get_setting(key, default))
    except (TypeError, ValueError):
        value = default
    if min_value is not None:
        value = max(min_value, value)
    if max_value is not None:
        value = min(max_value, value)
    return value

def ensure_default_records():
    for key, value in DEFAULT_SETTINGS.items():
        if not SystemSetting.query.filter_by(key=key).first():
            db.session.add(SystemSetting(key=key, value=value))

    admin = User.query.filter_by(username=DEFAULT_ADMIN_USERNAME).first()
    if not admin:
        admin = User(username=DEFAULT_ADMIN_USERNAME, role='admin', is_active=True)
        admin.set_password(DEFAULT_ADMIN_PASSWORD)
        db.session.add(admin)
    else:
        admin.role = 'admin'
        admin.is_active = True
        if admin.password == DEFAULT_ADMIN_PASSWORD or any(admin.check_password(password) for password in LEGACY_DEFAULT_ADMIN_PASSWORDS):
            admin.set_password(DEFAULT_ADMIN_PASSWORD)

    if not InviteCode.query.filter_by(code=DEFAULT_INVITE_CODE).first():
        db.session.add(InviteCode(code=DEFAULT_INVITE_CODE, note='Default registration invite code'))

    db.session.commit()

def log_audit(action, target_type=None, target_id=None, detail=None, actor=None):
    try:
        current_actor = actor or getattr(request, 'user', None)
        log = AuditLog(
            actor_id=current_actor.id if current_actor else None,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            detail=json.dumps(detail or {}, ensure_ascii=False),
            ip_address=request.remote_addr if request else None,
        )
        db.session.add(log)
    except RuntimeError:
        db.session.add(AuditLog(
            actor_id=actor.id if actor else None,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            detail=json.dumps(detail or {}, ensure_ascii=False),
        ))

def iso(dt):
    return dt.isoformat() if dt else None

def serialize_user(user):
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": iso(user.created_at),
        "last_login_at": iso(user.last_login_at),
        "token_expires_at": iso(user.token_expires_at),
    }

def serialize_invite(invite):
    return {
        "id": invite.id,
        "code": invite.code,
        "is_enabled": invite.is_enabled,
        "max_uses": invite.max_uses,
        "used_count": invite.used_count,
        "expires_at": iso(invite.expires_at),
        "note": invite.note,
        "created_at": iso(invite.created_at),
        "updated_at": iso(invite.updated_at),
        "is_valid": invite.is_valid(),
    }

def serialize_competition_admin(comp):
    return {
        "id": comp.id,
        "name": comp.name,
        "code": comp.code,
        "created_at": iso(comp.created_at),
        "archived_at": iso(comp.archived_at),
        "is_archived": comp.is_archived,
        "task_count": len(comp.tasks),
        "answer_count": sum(len(task.answers) for task in comp.tasks),
        "writeup_count": sum(len(task.writeups) for task in comp.tasks),
        "note_count": sum(len(task.notes) for task in comp.tasks),
    }

def parse_optional_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace('Z', '+00:00')).replace(tzinfo=None)

def upload_stats():
    root = app.config['UPLOAD_FOLDER']
    total_files = 0
    total_bytes = 0
    for current_root, _, files in os.walk(root):
        for filename in files:
            path = os.path.join(current_root, filename)
            try:
                total_files += 1
                total_bytes += os.path.getsize(path)
            except OSError:
                pass
    return {"files": total_files, "bytes": total_bytes}

def scan_upload_storage():
    root = os.path.join(app.config['UPLOAD_FOLDER'], 'wps')
    os.makedirs(root, exist_ok=True)

    referenced = set()
    for wp in Writeup.query.filter(Writeup.file_url.isnot(None)).all():
        referenced.add(wp.file_url.split('/')[-1])

    files = []
    orphans = []
    total_bytes = 0
    for filename in os.listdir(root):
        path = os.path.join(root, filename)
        if not os.path.isfile(path):
            continue
        size = os.path.getsize(path)
        total_bytes += size
        item = {
            "filename": filename,
            "size": size,
            "is_orphan": filename not in referenced,
            "download_url": f"/api/admin/storage/files/{filename}",
        }
        files.append(item)
        if item["is_orphan"]:
            orphans.append(item)

    return {
        "files": files,
        "orphans": orphans,
        "total_files": len(files),
        "total_bytes": total_bytes,
        "orphan_files": len(orphans),
        "orphan_bytes": sum(item["size"] for item in orphans),
    }

def sqlite_database_path():
    path = db.engine.url.database
    if not path:
        return None
    if os.path.isabs(path):
        return path
    return os.path.join(app.instance_path, path)

with app.app_context():
    ensure_schema()
    ensure_default_records()

# Decorator to require authentication
def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization')
        if token:
            token = token.replace('Bearer ', '')
        else:
            token = request.args.get('token')
            
        if not token:
            return jsonify({"error": "Unauthorized"}), 401
        
        user = User.query.filter_by(token=token).first()
        if not user:
            return jsonify({"error": "Invalid token"}), 401
        if user.token_expires_at and user.token_expires_at < datetime.utcnow():
            user.token = None
            user.token_expires_at = None
            db.session.commit()
            return jsonify({"error": "Token expired"}), 401
        if not user.is_active:
            return jsonify({"error": "User disabled"}), 403
        
        # Attach user to request
        request.user = user
        return f(*args, **kwargs)
    return wrapper

def require_admin(f):
    @wraps(f)
    @require_auth
    def wrapper(*args, **kwargs):
        if not request.user.is_admin:
            return jsonify({"error": "Admin permission required"}), 403
        return f(*args, **kwargs)
    return wrapper

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json or {}
    username = data.get('username')
    password = data.get('password')
    invite_value = data.get('inviteCode') or data.get('invite_code') or data.get('invite')
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    if not setting_enabled('registration_enabled', True):
        return jsonify({"error": "Registration disabled"}), 403
    if not invite_value:
        return jsonify({"error": "Invite code required"}), 400
        
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 400

    invite = InviteCode.query.filter_by(code=invite_value).first()
    if not invite or not invite.is_valid():
        return jsonify({"error": "Invalid invite code"}), 403
        
    new_user = User(username=username, role=get_setting('default_user_role', 'member'), is_active=True)
    new_user.set_password(password)
    invite.used_count += 1
    db.session.add(new_user)
    log_audit('user.register', 'user', username, {'invite_code': invite.code})
    db.session.commit()
    
    return jsonify({"message": "User registered successfully"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username).first()
        
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401
    if not user.is_active:
        return jsonify({"error": "User disabled"}), 403

    if user.password == password:
        user.set_password(password)
        
    # Generate simple token
    token = str(uuid.uuid4())
    now = datetime.utcnow()
    user.token = token
    user.last_login_at = now
    user.token_expires_at = now + timedelta(hours=int_setting('session_timeout_hours', 12, 1, 24 * 30))
    log_audit('user.login', 'user', user.id, {'username': user.username}, actor=user)
    db.session.commit()
    
    return jsonify({
        "message": "Login successful", 
        "token": token,
        "token_expires_at": iso(user.token_expires_at),
        "username": user.username,
        "role": user.role
    }), 200

@app.route('/api/admin/overview', methods=['GET'])
@require_admin
def admin_overview():
    storage = upload_stats()
    return jsonify({
        "users": User.query.count(),
        "active_users": User.query.filter_by(is_active=True).count(),
        "competitions": Competition.query.count(),
        "tasks": Task.query.count(),
        "answers": Answer.query.count(),
        "writeups": Writeup.query.count(),
        "notes": Note.query.count(),
        "invite_codes": InviteCode.query.count(),
        "audit_logs": AuditLog.query.count(),
        "upload_files": storage["files"],
        "upload_bytes": storage["bytes"],
    }), 200

@app.route('/api/admin/users', methods=['GET'])
@require_admin
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([serialize_user(user) for user in users]), 200

@app.route('/api/admin/users/<int:user_id>', methods=['PATCH'])
@require_admin
def admin_update_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.json or {}
    if 'role' in data:
        role = data.get('role')
        if role not in ('admin', 'member'):
            return jsonify({"error": "Invalid role"}), 400
        if user.id == request.user.id and role != 'admin':
            return jsonify({"error": "Cannot change your own admin role"}), 400
        user.role = role

    if 'is_active' in data:
        next_active = bool(data.get('is_active'))
        if user.id == request.user.id and not next_active:
            return jsonify({"error": "Cannot disable current admin user"}), 400
        user.is_active = next_active
        if not next_active:
            user.token = None
            user.token_expires_at = None

    log_audit('admin.user.update', 'user', user.id, data)
    db.session.commit()
    return jsonify(serialize_user(user)), 200

@app.route('/api/admin/users/<int:user_id>/reset-password', methods=['POST'])
@require_admin
def admin_reset_user_password(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.json or {}
    new_password = data.get('password') or generate_task_code(12)
    user.set_password(new_password)
    user.token = None
    user.token_expires_at = None
    log_audit('admin.user.reset_password', 'user', user.id)
    db.session.commit()
    return jsonify({"message": "Password reset successfully", "password": new_password}), 200

@app.route('/api/admin/change-password', methods=['POST'])
@require_admin
def admin_change_password():
    data = request.json or {}
    current_password = data.get('current_password')
    new_password = data.get('new_password')

    if not current_password or not new_password:
        return jsonify({"error": "Current and new password required"}), 400
    if not request.user.check_password(current_password):
        return jsonify({"error": "Current password incorrect"}), 400
    if len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters"}), 400

    request.user.set_password(new_password)
    request.user.token = None
    request.user.token_expires_at = None
    log_audit('admin.self.change_password', 'user', request.user.id)
    db.session.commit()
    return jsonify({"message": "Password changed successfully"}), 200

@app.route('/api/admin/invite-codes', methods=['GET'])
@require_admin
def admin_invite_codes():
    invites = InviteCode.query.order_by(InviteCode.created_at.desc()).all()
    return jsonify([serialize_invite(invite) for invite in invites]), 200

@app.route('/api/admin/invite-codes', methods=['POST'])
@require_admin
def admin_create_invite_code():
    data = request.json or {}
    code = (data.get('code') or generate_task_code(8)).strip()
    if not code:
        return jsonify({"error": "Invite code required"}), 400
    if InviteCode.query.filter_by(code=code).first():
        return jsonify({"error": "Invite code already exists"}), 400

    invite = InviteCode(
        code=code,
        is_enabled=bool(data.get('is_enabled', True)),
        max_uses=data.get('max_uses'),
        expires_at=parse_optional_datetime(data.get('expires_at')),
        note=data.get('note'),
        created_by_id=request.user.id,
    )
    db.session.add(invite)
    log_audit('admin.invite.create', 'invite_code', code)
    db.session.commit()
    return jsonify(serialize_invite(invite)), 201

@app.route('/api/admin/invite-codes/<int:invite_id>', methods=['PATCH'])
@require_admin
def admin_update_invite_code(invite_id):
    invite = db.session.get(InviteCode, invite_id)
    if not invite:
        return jsonify({"error": "Invite code not found"}), 404

    data = request.json or {}
    if 'is_enabled' in data:
        invite.is_enabled = bool(data.get('is_enabled'))
    if 'max_uses' in data:
        invite.max_uses = data.get('max_uses')
    if 'expires_at' in data:
        invite.expires_at = parse_optional_datetime(data.get('expires_at'))
    if 'note' in data:
        invite.note = data.get('note')

    log_audit('admin.invite.update', 'invite_code', invite.id, data)
    db.session.commit()
    return jsonify(serialize_invite(invite)), 200

@app.route('/api/admin/settings', methods=['GET'])
@require_admin
def admin_get_settings():
    settings = SystemSetting.query.order_by(SystemSetting.key.asc()).all()
    return jsonify({setting.key: setting.value for setting in settings}), 200

@app.route('/api/admin/settings', methods=['PATCH'])
@require_admin
def admin_update_settings():
    data = request.json or {}
    for key, value in data.items():
        if key in DEFAULT_SETTINGS:
            set_setting(key, value)
    log_audit('admin.settings.update', 'system_setting', None, data)
    db.session.commit()
    return admin_get_settings()

@app.route('/api/admin/audit-logs', methods=['GET'])
@require_admin
def admin_audit_logs():
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(100).all()
    return jsonify([{
        "id": log.id,
        "actor": log.actor.username if log.actor else None,
        "action": log.action,
        "target_type": log.target_type,
        "target_id": log.target_id,
        "detail": json.loads(log.detail) if log.detail else {},
        "ip_address": log.ip_address,
        "created_at": iso(log.created_at),
    } for log in logs]), 200

@app.route('/api/admin/competitions', methods=['GET'])
@require_admin
def admin_competitions():
    comps = Competition.query.order_by(Competition.created_at.desc()).all()
    return jsonify([serialize_competition_admin(comp) for comp in comps]), 200

@app.route('/api/admin/competitions/<int:comp_id>', methods=['PATCH'])
@require_admin
def admin_update_competition(comp_id):
    comp = db.session.get(Competition, comp_id)
    if not comp:
        return jsonify({"error": "Competition not found"}), 404

    data = request.json or {}
    if 'is_archived' in data:
        comp.archived_at = datetime.utcnow() if data.get('is_archived') else None
    if 'name' in data:
        name = str(data.get('name') or '').strip()
        if not name:
            return jsonify({"error": "Competition name required"}), 400
        comp.name = name

    log_audit('admin.competition.update', 'competition', comp.id, data)
    db.session.commit()
    announcer.announce(json.dumps({"action": "refresh"}))
    return jsonify(serialize_competition_admin(comp)), 200

@app.route('/api/admin/storage', methods=['GET'])
@require_admin
def admin_storage():
    return jsonify(scan_upload_storage()), 200

@app.route('/api/admin/storage/orphans', methods=['DELETE'])
@require_admin
def admin_delete_orphan_files():
    scan = scan_upload_storage()
    root = os.path.join(app.config['UPLOAD_FOLDER'], 'wps')
    deleted = []
    for item in scan["orphans"]:
        path = os.path.join(root, item["filename"])
        try:
            os.remove(path)
            deleted.append(item["filename"])
        except OSError:
            pass

    log_audit('admin.storage.delete_orphans', 'storage', None, {'deleted': deleted})
    db.session.commit()
    return jsonify({"deleted": deleted, "count": len(deleted)}), 200

@app.route('/api/admin/storage/files/<path:filename>', methods=['GET'])
@require_admin
def admin_download_storage_file(filename):
    root = os.path.join(app.config['UPLOAD_FOLDER'], 'wps')
    safe_filename = os.path.basename(filename)
    if not safe_filename or safe_filename != filename:
        return jsonify({"error": "Invalid filename"}), 400
    file_path = os.path.join(root, safe_filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    log_audit('admin.storage.download_file', 'storage_file', safe_filename)
    db.session.commit()
    return send_from_directory(root, safe_filename, as_attachment=True)

@app.route('/api/admin/backup/database', methods=['GET'])
@require_admin
def admin_backup_database():
    path = sqlite_database_path()
    if not path or not os.path.exists(path):
        return jsonify({"error": "Database file not found"}), 404

    log_audit('admin.backup.database', 'database')
    db.session.commit()
    return send_file(
        path,
        as_attachment=True,
        download_name=f"yggdrasil_os_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.db",
    )

@app.route('/api/competitions', methods=['POST'])
@require_auth
def create_competition():
    data = request.json
    name = data.get('name')
    if not name:
        return jsonify({"error": "Competition name required"}), 400
        
    code = generate_task_code(6)
    comp = Competition(name=name, code=code)
    db.session.add(comp)
    db.session.commit()
    
    return jsonify({
        "message": "Competition created successfully",
        "id": comp.id,
        "name": comp.name,
        "code": comp.code
    }), 201

@app.route('/api/competitions', methods=['GET'])
@require_auth
def get_competitions():
    comps = Competition.query.order_by(Competition.created_at.desc()).all()
    result = []
    for c in comps:
        result.append({
            "id": c.id,
            "name": c.name,
            "code": c.code,
            "task_count": len(c.tasks),
            "created_at": c.created_at.isoformat() if c.created_at else None
        })
    return jsonify(result), 200

@app.route('/api/competitions/<int:comp_id>', methods=['GET'])
@require_auth
def get_competition_detail(comp_id):
    comp = db.session.get(Competition, comp_id)
    if not comp:
        return jsonify({"error": "Competition not found"}), 404
        
    return jsonify({
        "id": comp.id,
        "name": comp.name,
        "code": comp.code,
        "created_at": comp.created_at.isoformat() if comp.created_at else None
    }), 200

@app.route('/api/competitions/<int:comp_id>', methods=['DELETE'])
@require_auth
def delete_competition(comp_id):
    if not request.user.is_admin:
        return jsonify({"error": "Permission denied"}), 403
        
    comp = db.session.get(Competition, comp_id)
    if not comp:
        return jsonify({"error": "Competition not found"}), 404
        
    # Manually delete related tasks to trigger file cleanup and avoid FK issues
    tasks = Task.query.filter_by(competition_id=comp_id).all()
    for task in tasks:
        # Delete related files
        for wp in task.writeups:
            if wp.file_url:
                try:
                    filename = wp.file_url.split('/')[-1]
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'wps', filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    pass
        
        Answer.query.filter_by(task_id=task.id).delete()
        Writeup.query.filter_by(task_id=task.id).delete()
        Note.query.filter_by(task_id=task.id).delete()
        db.session.delete(task)
        
    db.session.delete(comp)
    db.session.commit()
    
    return jsonify({"message": "Competition deleted successfully"}), 200

@app.route('/api/tasks/upload', methods=['POST'])
@require_auth
def upload_tasks():
    comp_id = request.form.get('competition_id')
    if not comp_id:
        return jsonify({"error": "competition_id required"}), 400
        
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    try:
        # Use pandas to read excel (requires openpyxl or xlrd)
        df = pd.read_excel(file)
        
        # Ensure correct columns exist
        # Expected columns: 题目id, 题目内容, 题目选项
        if len(df.columns) < 2:
            return jsonify({"error": "Excel format incorrect, at least 2 columns needed"}), 400
            
        col_id = df.columns[0]
        col_content = df.columns[1]
        
        tasks_added = 0
        for index, row in df.iterrows():
            raw_task_id = str(row[col_id])
            
            if pd.isna(raw_task_id) or raw_task_id == 'nan' or not raw_task_id.strip():
                continue
                
            # Prefix the task ID with the competition ID to ensure uniqueness across competitions
            task_id = f"{comp_id}_{raw_task_id.strip()}"
                
            task = db.session.get(Task, task_id)
            if not task:
                task = Task(id=task_id, competition_id=comp_id)
                db.session.add(task)
            elif str(task.competition_id) != str(comp_id):
                # If a task exists with this ID but belongs to a different competition,
                # it means the prefixing failed or was bypassed somehow.
                # In normal flow, prefixed ID ensures uniqueness per competition.
                continue
                
            task.content = str(row[col_content])
                
            tasks_added += 1
            
        db.session.commit()
        announcer.announce(json.dumps({"action": "refresh"}))
        return jsonify({"message": f"{tasks_added} tasks uploaded successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks/batch-update', methods=['POST'])
@require_auth
def batch_update_tasks():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    comp_id = request.form.get('competition_id')
        
    try:
        df = pd.read_excel(file)
        
        # Check required column
        if '题目ID' not in df.columns:
            return jsonify({"error": "Excel format incorrect, '题目ID' column is required"}), 400
            
        updates_count = 0
        for index, row in df.iterrows():
            raw_task_id = str(row['题目ID'])
            
            if pd.isna(raw_task_id) or raw_task_id == 'nan' or not raw_task_id.strip():
                continue
                
            # For backward compatibility, check if the raw ID exists. If not, use prefixed ID.
            # We assume batch update provides the original raw ID from Excel.
            task_id = raw_task_id.strip()
            task = db.session.get(Task, task_id)
            
            # If the raw task belongs to a different competition, ignore it and try prefix
            if task and comp_id and str(task.competition_id) != str(comp_id):
                task = None
            
            if not task:
                # Try with prefix
                if comp_id:
                    task_id = f"{comp_id}_{raw_task_id.strip()}"
                    task = db.session.get(Task, task_id)
            
            if not task:
                continue
                
            # If competition_id is provided, only update tasks in that competition
            if comp_id and str(task.competition_id) != str(comp_id):
                continue
            
            has_updates = False
            
            # Update Answer
            if '答案' in df.columns:
                answer_content = str(row['答案']) if not pd.isna(row['答案']) else ''
                if answer_content.strip():
                    existing_answer = Answer.query.filter_by(task_id=task_id, user_id=request.user.id).first()
                    if existing_answer:
                        existing_answer.content = answer_content
                    else:
                        new_answer = Answer(task_id=task_id, user_id=request.user.id, content=answer_content)
                        db.session.add(new_answer)
                    has_updates = True
                    
            # Update Writeup (WP)
            wp_col = 'WP (Writeup)' if 'WP (Writeup)' in df.columns else 'WP' if 'WP' in df.columns else None
            if wp_col:
                wp_content = str(row[wp_col]) if not pd.isna(row[wp_col]) else ''
                if wp_content.strip():
                    new_wp = Writeup(task_id=task_id, user_id=request.user.id, content=wp_content)
                    db.session.add(new_wp)
                    has_updates = True
                    
            # Update Note
            if '备注' in df.columns:
                note_content = str(row['备注']) if not pd.isna(row['备注']) else ''
                if note_content.strip():
                    new_note = Note(task_id=task_id, user_id=request.user.id, content=note_content)
                    db.session.add(new_note)
                    has_updates = True
                    
            if has_updates:
                updates_count += 1
            
        db.session.commit()
        announcer.announce(json.dumps({"action": "refresh"}))
        return jsonify({"message": f"Successfully updated {updates_count} tasks"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks/single', methods=['POST'])
@require_auth
def create_single_task():
    data = request.json
    competition_id = data.get('competition_id')
    content = data.get('content')
    
    if not content or not competition_id:
        return jsonify({"error": "Content and competition_id required"}), 400
        
    raw_task_id = str(uuid.uuid4())
    task_id = f"{competition_id}_{raw_task_id}"
    
    task = Task(id=task_id, competition_id=competition_id, content=content)
    db.session.add(task)
    db.session.commit()
    
    announcer.announce(json.dumps({"action": "refresh", "task_id": task_id}))
    return jsonify({
        "message": "Task created successfully", 
        "id": task.id
    }), 201

@app.route('/api/tasks/<task_id>/pin', methods=['POST'])
@require_auth
def toggle_pin_task(task_id):
    if not request.user.is_admin:
        return jsonify({"error": "Permission denied"}), 403
        
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
        
    if task.pinned_at:
        task.pinned_at = None
        msg = "Task unpinned successfully"
    else:
        task.pinned_at = datetime.utcnow()
        msg = "Task pinned successfully"
        
    db.session.commit()
    announcer.announce(json.dumps({"action": "refresh", "task_id": task_id}))
    
    return jsonify({"message": msg, "pinned": task.pinned_at is not None}), 200

@app.route('/api/tasks', methods=['GET'])
@require_auth
def get_tasks():
    comp_id = request.args.get('competition_id')
    query = Task.query
    if comp_id:
        query = query.filter_by(competition_id=comp_id)
        
    tasks = query.order_by(Task.created_at.desc()).all()
    result = []
    
    for task in tasks:
        # Return full task data for the competition board
        task_data = {
            "id": task.id,
            "content": task.content,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "pinned_at": task.pinned_at.isoformat() if task.pinned_at else None,
            "answers": [{"id": a.id, "user": a.user.username, "content": a.content} for a in task.answers],
            "wps": [{"id": w.id, "user": w.user.username, "content": w.content, "file_url": w.file_url, "file_type": w.file_type, "original_filename": w.original_filename, "likes": len(w.likes), "liked_by_me": any(l.user_id == request.user.id for l in w.likes)} for w in task.writeups],
            "notes": [{"id": n.id, "user": n.user.username, "content": n.content, "likes": len(n.likes), "liked_by_me": any(l.user_id == request.user.id for l in n.likes)} for n in task.notes]
        }
        result.append(task_data)
        
    return jsonify(result), 200

@app.route('/api/tasks/<task_id>', methods=['GET'])
@require_auth
def get_task_detail(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
        
    task_data = {
        "id": task.id,
        "content": task.content,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "pinned_at": task.pinned_at.isoformat() if task.pinned_at else None,
        "answers": [{"id": a.id, "user": a.user.username, "content": a.content} for a in task.answers],
        "wps": [{"id": w.id, "user": w.user.username, "content": w.content, "file_url": w.file_url, "file_type": w.file_type, "original_filename": w.original_filename, "likes": len(w.likes), "liked_by_me": any(l.user_id == request.user.id for l in w.likes)} for w in task.writeups],
        "notes": [{"id": n.id, "user": n.user.username, "content": n.content, "likes": len(n.likes), "liked_by_me": any(l.user_id == request.user.id for l in n.likes)} for n in task.notes]
    }
    
    return jsonify(task_data), 200

@app.route('/api/tasks/<task_id>', methods=['PUT'])
@require_auth
def update_task(task_id):
    if not request.user.is_admin:
        return jsonify({"error": "Permission denied"}), 403
        
    data = request.json
    new_content = data.get('content')
    new_display_id = data.get('displayId')
    
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
        
    if new_content is not None:
        task.content = new_content
        
    if new_display_id is not None:
        # SQLite doesn't easily allow updating primary keys that are referenced by foreign keys.
        # So we have to create a new task with the new ID, move all relations, and delete the old one.
        # But first, construct the new real ID
        new_real_id = f"{task.competition_id}_{new_display_id}"
        
        if new_real_id != task_id:
            # Check if target ID already exists
            existing_task = db.session.get(Task, new_real_id)
            if existing_task:
                return jsonify({"error": f"Task with ID {new_display_id} already exists in this competition"}), 400
                
            # Create new task
            new_task = Task(id=new_real_id, competition_id=task.competition_id, content=task.content, created_at=task.created_at, pinned_at=task.pinned_at)
            db.session.add(new_task)
            
            # Move answers
            for a in task.answers:
                a.task_id = new_real_id
            
            # Move writeups
            for w in task.writeups:
                w.task_id = new_real_id
                
            # Move notes
            for n in task.notes:
                n.task_id = new_real_id
                
            # Delete old task
            db.session.delete(task)
            task_id = new_real_id # Update for response
        
    db.session.commit()
    announcer.announce(json.dumps({"action": "refresh", "task_id": task_id}))
    return jsonify({"message": "Task updated successfully", "content": new_content, "new_id": task_id}), 200

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
@require_auth
def delete_task(task_id):
    if not request.user.is_admin:
        return jsonify({"error": "Permission denied"}), 403
        
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
        
    # Delete related files
    for wp in task.writeups:
        if wp.file_url:
            try:
                filename = wp.file_url.split('/')[-1]
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'wps', filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Error deleting file: {e}")
                
    # Manually delete related records to bypass SQLite PRAGMA foreign_keys issues
    Answer.query.filter_by(task_id=task_id).delete()
    Writeup.query.filter_by(task_id=task_id).delete()
    Note.query.filter_by(task_id=task_id).delete()
                
    db.session.delete(task)
    db.session.commit()
    announcer.announce(json.dumps({"action": "refresh"}))
    
    return jsonify({"message": "Task deleted successfully"}), 200

@app.route('/api/tasks/<task_id>/<type>', methods=['POST'])
@require_auth
def add_item(task_id, type):
    """type can be 'answer', 'wp', or 'note'"""
    # handle multipart/form-data for WP with file
    if type == 'wp' and request.content_type and request.content_type.startswith('multipart/form-data'):
        content = request.form.get('content', '')
        file = request.files.get('file')
    else:
        data = request.json or {}
        content = data.get('content', '')
        file = None
    
    if not content and not file:
        return jsonify({"error": "Content or file required"}), 400
        
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
        
    if type == 'answer':
        # Check if the user already has an answer for this task
        existing_answer = Answer.query.filter_by(task_id=task_id, user_id=request.user.id).first()
        if existing_answer:
            existing_answer.content = content
            existing_answer.created_at = datetime.utcnow()
            new_item = existing_answer
            is_new = False
        else:
            new_item = Answer(task_id=task_id, user_id=request.user.id, content=content)
            db.session.add(new_item)
            is_new = True
            
    elif type == 'wp':
        file_url = None
        file_type = None
        original_filename = None
        if file and file.filename != '':
            original_filename = file.filename
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'wps', unique_filename)
            file.save(file_path)
            file_url = f"/api/uploads/wps/{unique_filename}"
            
            # Determine file type roughly
            ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']:
                file_type = 'image'
            elif ext in ['zip', 'rar', '7z', 'tar', 'gz']:
                file_type = 'archive'
            else:
                file_type = 'other'

        new_item = Writeup(task_id=task_id, user_id=request.user.id, content=content, file_url=file_url, file_type=file_type, original_filename=original_filename)
        db.session.add(new_item)
        is_new = True
        
    elif type == 'note':
        new_item = Note(task_id=task_id, user_id=request.user.id, content=content)
        db.session.add(new_item)
        is_new = True
        
    else:
        return jsonify({"error": "Invalid type"}), 400
        
    db.session.commit()
    
    response_data = {
        "message": f"{type} added/updated successfully", 
        "id": new_item.id, 
        "user": request.user.username,
        "is_new": is_new
    }
    
    if type == 'wp':
        response_data['file_url'] = new_item.file_url
        response_data['file_type'] = new_item.file_type
        response_data['original_filename'] = new_item.original_filename
        
    announcer.announce(json.dumps({"action": "refresh", "task_id": task_id}))
    return jsonify(response_data), 200

@app.route('/api/items/<type>/<int:item_id>/like', methods=['POST'])
@require_auth
def toggle_like(type, item_id):
    """type can be 'wp' or 'note'"""
    if type == 'wp':
        item = db.session.get(Writeup, item_id)
        if not item:
            return jsonify({"error": "WP not found"}), 404
        like = WriteupLike.query.filter_by(writeup_id=item_id, user_id=request.user.id).first()
        if like:
            db.session.delete(like)
            liked = False
        else:
            db.session.add(WriteupLike(writeup_id=item_id, user_id=request.user.id))
            liked = True
    elif type == 'note':
        item = db.session.get(Note, item_id)
        if not item:
            return jsonify({"error": "Note not found"}), 404
        like = NoteLike.query.filter_by(note_id=item_id, user_id=request.user.id).first()
        if like:
            db.session.delete(like)
            liked = False
        else:
            db.session.add(NoteLike(note_id=item_id, user_id=request.user.id))
            liked = True
    else:
        return jsonify({"error": "Invalid type for likes"}), 400
        
    db.session.commit()
    announcer.announce(json.dumps({"action": "refresh", "task_id": item.task_id}))
    return jsonify({"message": "Success", "liked": liked}), 200

@app.route('/api/items/<type>/<int:item_id>', methods=['PUT'])
@require_auth
def edit_item(type, item_id):
    """type can be 'answer', 'wp', or 'note'"""
    data = request.json
    new_content = data.get('content')
    
    if not new_content:
        return jsonify({"error": "New content required"}), 400
        
    if type == 'answer':
        item = db.session.get(Answer, item_id)
    elif type == 'wp':
        item = db.session.get(Writeup, item_id)
    elif type == 'note':
        item = db.session.get(Note, item_id)
    else:
        return jsonify({"error": "Invalid type"}), 400
        
    if not item:
        return jsonify({"error": f"{type} not found"}), 404
        
    if item.user_id != request.user.id and not request.user.is_admin:
        return jsonify({"error": "Permission denied"}), 403
        
    item.content = new_content
    db.session.commit()
    
    announcer.announce(json.dumps({"action": "refresh", "task_id": item.task_id}))
    return jsonify({"message": f"{type} updated successfully", "content": new_content}), 200

@app.route('/api/items/<type>/<int:item_id>', methods=['DELETE'])
@require_auth
def delete_item(type, item_id):
    """type can be 'answer', 'wp', or 'note'"""
    if type == 'answer':
        item = db.session.get(Answer, item_id)
    elif type == 'wp':
        item = db.session.get(Writeup, item_id)
    elif type == 'note':
        item = db.session.get(Note, item_id)
    else:
        return jsonify({"error": "Invalid type"}), 400
        
    if not item:
        return jsonify({"error": f"{type} not found"}), 404
        
    if item.user_id != request.user.id and not request.user.is_admin:
        return jsonify({"error": "Permission denied"}), 403
        
    # Delete file if it exists (for WP)
    if type == 'wp' and item.file_url:
        try:
            filename = item.file_url.split('/')[-1]
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'wps', filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file: {e}")
            
    # Save task_id before deleting
    task_id = item.task_id
    
    db.session.delete(item)
    db.session.commit()
    
    announcer.announce(json.dumps({"action": "refresh", "task_id": task_id}))
    return jsonify({"message": f"{type} deleted successfully"}), 200

@app.route('/api/uploads/wps/<filename>')
def uploaded_wp_file(filename):
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], 'wps'), filename)

@app.route('/api/stream')
def stream():
    def event_stream():
        messages = announcer.listen()
        while True:
            msg = messages.get()  # blocks until message is available
            yield f"data: {msg}\n\n"
    return app.response_class(event_stream(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
