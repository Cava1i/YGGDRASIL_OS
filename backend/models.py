from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    token = db.Column(db.String(120), unique=True, nullable=True)
    token_expires_at = db.Column(db.DateTime, nullable=True)
    role = db.Column(db.String(20), nullable=False, default='member')
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    last_login_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        if not self.password:
            return False

        is_hash = self.password.startswith(('scrypt:', 'pbkdf2:', 'sha256:'))
        if is_hash:
            return check_password_hash(self.password, raw_password)

        # Backward compatibility for users created before password hashing.
        return self.password == raw_password

    @property
    def is_admin(self):
        return self.role == 'admin' and self.is_active

class Competition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    archived_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_archived(self):
        return self.archived_at is not None

class Task(db.Model):
    id = db.Column(db.String(80), primary_key=True)
    competition_id = db.Column(db.Integer, db.ForeignKey('competition.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    pinned_at = db.Column(db.DateTime, nullable=True)

    competition = db.relationship('Competition', backref=db.backref('tasks', lazy=True, cascade="all, delete-orphan"))
    
class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(80), db.ForeignKey('task.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('answers', lazy=True))
    task = db.relationship('Task', backref=db.backref('answers', lazy=True, cascade="all, delete-orphan"))

class Writeup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(80), db.ForeignKey('task.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=True) # WP text can be null if it's only a file
    file_url = db.Column(db.String(255), nullable=True) # To store file path/URL
    file_type = db.Column(db.String(50), nullable=True) # e.g. 'image', 'archive'
    original_filename = db.Column(db.String(255), nullable=True) # Store original filename
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('writeups', lazy=True))
    task = db.relationship('Task', backref=db.backref('writeups', lazy=True, cascade="all, delete-orphan"))

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(80), db.ForeignKey('task.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('notes', lazy=True))
    task = db.relationship('Task', backref=db.backref('notes', lazy=True, cascade="all, delete-orphan"))

class WriteupLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    writeup_id = db.Column(db.Integer, db.ForeignKey('writeup.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    writeup = db.relationship('Writeup', backref=db.backref('likes', lazy=True, cascade="all, delete-orphan"))
    user = db.relationship('User', backref=db.backref('writeup_likes', lazy=True))

class NoteLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    note = db.relationship('Note', backref=db.backref('likes', lazy=True, cascade="all, delete-orphan"))
    user = db.relationship('User', backref=db.backref('note_likes', lazy=True))

class InviteCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(80), unique=True, nullable=False)
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)
    max_uses = db.Column(db.Integer, nullable=True)
    used_count = db.Column(db.Integer, nullable=False, default=0)
    expires_at = db.Column(db.DateTime, nullable=True)
    note = db.Column(db.String(255), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by = db.relationship('User', backref=db.backref('created_invite_codes', lazy=True))

    def is_valid(self, now=None):
        now = now or datetime.utcnow()
        if not self.is_enabled:
            return False
        if self.expires_at and self.expires_at < now:
            return False
        if self.max_uses is not None and self.used_count >= self.max_uses:
            return False
        return True

class SystemSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    action = db.Column(db.String(80), nullable=False)
    target_type = db.Column(db.String(80), nullable=True)
    target_id = db.Column(db.String(80), nullable=True)
    detail = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(80), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    actor = db.relationship('User', backref=db.backref('audit_logs', lazy=True))
