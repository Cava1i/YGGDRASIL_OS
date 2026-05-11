<script setup>
import { computed, onMounted, ref } from 'vue'
import { api, API_BASE } from '../api'

const token = ref(localStorage.getItem('token') || '')
const currentUsername = ref(localStorage.getItem('username') || '')
const activeTab = ref('overview')
const loading = ref(false)
const error = ref('')
const notice = ref('')

const overview = ref({})
const users = ref([])
const inviteCodes = ref([])
const competitions = ref([])
const storage = ref({ files: [], orphans: [] })
const settings = ref({})
const auditLogs = ref([])

const inviteForm = ref({ code: '', max_uses: '', note: '' })
const resetPassword = ref({})
const passwordForm = ref({ current_password: '', new_password: '' })

const tabs = [
  { key: 'overview', label: '概览' },
  { key: 'users', label: '用户' },
  { key: 'invites', label: '邀请码' },
  { key: 'competitions', label: '比赛' },
  { key: 'storage', label: '附件' },
  { key: 'backup', label: '备份' },
  { key: 'settings', label: '配置' },
  { key: 'logs', label: '日志' }
]

const headers = computed(() => ({ Authorization: `Bearer ${token.value}` }))
const backupUrl = computed(() => `${API_BASE}/api/admin/backup/database?token=${encodeURIComponent(token.value)}`)

const isSelf = (user) => user.username === currentUsername.value

const showNotice = (text) => {
  notice.value = text
  window.setTimeout(() => {
    if (notice.value === text) notice.value = ''
  }, 2600)
}

const formatBytes = (bytes = 0) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

const formatDate = (value) => {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

const storageDownloadUrl = (file) => {
  return `${API_BASE}${file.download_url}?token=${encodeURIComponent(token.value)}`
}

const fetchAdminData = async () => {
  loading.value = true
  error.value = ''
  try {
    const [overviewRes, usersRes, invitesRes, competitionsRes, storageRes, settingsRes, logsRes] = await Promise.all([
      api.get('/api/admin/overview', { headers: headers.value }),
      api.get('/api/admin/users', { headers: headers.value }),
      api.get('/api/admin/invite-codes', { headers: headers.value }),
      api.get('/api/admin/competitions', { headers: headers.value }),
      api.get('/api/admin/storage', { headers: headers.value }),
      api.get('/api/admin/settings', { headers: headers.value }),
      api.get('/api/admin/audit-logs', { headers: headers.value })
    ])

    overview.value = overviewRes.data
    users.value = usersRes.data
    inviteCodes.value = invitesRes.data
    competitions.value = competitionsRes.data
    storage.value = storageRes.data
    settings.value = settingsRes.data
    auditLogs.value = logsRes.data
  } catch (err) {
    error.value = err.response?.data?.error || '无法加载管理后台数据'
  } finally {
    loading.value = false
  }
}

const createInvite = async () => {
  error.value = ''
  try {
    await api.post('/api/admin/invite-codes', {
      code: inviteForm.value.code,
      max_uses: inviteForm.value.max_uses ? Number(inviteForm.value.max_uses) : null,
      note: inviteForm.value.note
    }, { headers: headers.value })
    inviteForm.value = { code: '', max_uses: '', note: '' }
    showNotice('邀请码已创建')
    await fetchAdminData()
  } catch (err) {
    error.value = err.response?.data?.error || '创建邀请码失败'
  }
}

const toggleInvite = async (invite) => {
  await api.patch(`/api/admin/invite-codes/${invite.id}`, {
    is_enabled: !invite.is_enabled
  }, { headers: headers.value })
  showNotice('邀请码已更新')
  await fetchAdminData()
}

const updateUser = async (user, payload) => {
  error.value = ''
  try {
    await api.patch(`/api/admin/users/${user.id}`, payload, { headers: headers.value })
    showNotice('用户已更新')
    await fetchAdminData()
  } catch (err) {
    error.value = err.response?.data?.error || '更新用户失败'
  }
}

const resetUserPassword = async (user) => {
  error.value = ''
  try {
    const password = resetPassword.value[user.id]
    const res = await api.post(`/api/admin/users/${user.id}/reset-password`, {
      password
    }, { headers: headers.value })
    resetPassword.value[user.id] = ''
    showNotice(`新密码：${res.data.password}`)
  } catch (err) {
    error.value = err.response?.data?.error || '重置密码失败'
  }
}

const changeOwnPassword = async () => {
  error.value = ''
  try {
    await api.post('/api/admin/change-password', passwordForm.value, {
      headers: headers.value
    })
    passwordForm.value = { current_password: '', new_password: '' }
    localStorage.removeItem('token')
    showNotice('密码已修改，请重新登录')
    window.setTimeout(() => window.location.assign('/'), 1200)
  } catch (err) {
    error.value = err.response?.data?.error || '修改密码失败'
  }
}

const toggleCompetitionArchive = async (competition) => {
  await api.patch(`/api/admin/competitions/${competition.id}`, {
    is_archived: !competition.is_archived
  }, { headers: headers.value })
  showNotice('比赛状态已更新')
  await fetchAdminData()
}

const deleteOrphans = async () => {
  if (!window.confirm('确认清理所有孤立附件？')) return
  await api.delete('/api/admin/storage/orphans', { headers: headers.value })
  showNotice('孤立附件已清理')
  await fetchAdminData()
}

const saveSettings = async () => {
  error.value = ''
  try {
    await api.patch('/api/admin/settings', settings.value, { headers: headers.value })
    showNotice('配置已保存')
    await fetchAdminData()
  } catch (err) {
    error.value = err.response?.data?.error || '保存配置失败'
  }
}

onMounted(fetchAdminData)
</script>

<template>
  <div class="admin-console page-shell">
    <header class="admin-hero">
      <div>
        <p class="page-kicker">ADMIN WAR ROOM</p>
        <h2>管理员战情室</h2>
        <p>用户、邀请码、比赛、附件、备份和系统配置集中管理。</p>
      </div>
      <div class="hero-actions">
        <a class="download-link backup-mini" :href="backupUrl" download>数据库备份</a>
        <button @click="fetchAdminData">刷新态势</button>
      </div>
    </header>

    <div class="tab-row">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="tab-button"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <p v-if="error" class="state-message error">{{ error }}</p>
    <p v-if="notice" class="state-message success">{{ notice }}</p>
    <p v-if="loading" class="state-message">加载中...</p>

    <section v-if="activeTab === 'overview'" class="admin-section">
      <div class="metric-grid">
        <div class="metric"><span>注册用户</span><strong>{{ overview.users || 0 }}</strong></div>
        <div class="metric"><span>活跃用户</span><strong>{{ overview.active_users || 0 }}</strong></div>
        <div class="metric"><span>比赛行动</span><strong>{{ overview.competitions || 0 }}</strong></div>
        <div class="metric"><span>题目目标</span><strong>{{ overview.tasks || 0 }}</strong></div>
        <div class="metric"><span>答案记录</span><strong>{{ overview.answers || 0 }}</strong></div>
        <div class="metric"><span>Writeup</span><strong>{{ overview.writeups || 0 }}</strong></div>
        <div class="metric"><span>附件</span><strong>{{ overview.upload_files || 0 }}</strong></div>
        <div class="metric"><span>存储占用</span><strong>{{ formatBytes(overview.upload_bytes) }}</strong></div>
      </div>
    </section>

    <section v-if="activeTab === 'users'" class="admin-section">
      <div class="section-head">
        <div>
          <p class="page-kicker">ACCESS CONTROL</p>
          <h3>用户席位</h3>
        </div>
      </div>

      <form class="password-form" @submit.prevent="changeOwnPassword">
        <input v-model="passwordForm.current_password" type="password" placeholder="当前管理员密码" required />
        <input v-model="passwordForm.new_password" type="password" placeholder="新密码" required />
        <button type="submit">修改我的密码</button>
      </form>

      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>用户名</th>
              <th>角色</th>
              <th>状态</th>
              <th>注册时间</th>
              <th>最近登录</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id">
              <td>
                <strong>{{ user.username }}</strong>
                <span v-if="isSelf(user)" class="self-chip">当前账号</span>
              </td>
              <td>
                <select
                  :value="user.role"
                  :disabled="isSelf(user)"
                  @change="updateUser(user, { role: $event.target.value })"
                >
                  <option value="member">member</option>
                  <option value="admin">admin</option>
                </select>
                <span v-if="isSelf(user)" class="self-note">当前管理员不可降级，避免失去后台入口。</span>
              </td>
              <td>
                <span class="status-pill" :class="user.is_active ? 'ok' : 'danger'">
                  {{ user.is_active ? '启用' : '禁用' }}
                </span>
              </td>
              <td>{{ formatDate(user.created_at) }}</td>
              <td>{{ formatDate(user.last_login_at) }}</td>
              <td class="actions">
                <button :disabled="isSelf(user)" @click="updateUser(user, { is_active: !user.is_active })">
                  {{ user.is_active ? '禁用' : '启用' }}
                </button>
                <input v-model="resetPassword[user.id]" type="text" placeholder="新密码，可留空" />
                <button @click="resetUserPassword(user)">重置</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="activeTab === 'invites'" class="admin-section">
      <div class="section-head">
        <div>
          <p class="page-kicker">INVITE CHANNEL</p>
          <h3>邀请码配置</h3>
        </div>
      </div>

      <form class="inline-form" @submit.prevent="createInvite">
        <input v-model="inviteForm.code" type="text" placeholder="邀请码" required />
        <input v-model="inviteForm.max_uses" type="number" min="1" placeholder="次数" />
        <input v-model="inviteForm.note" type="text" placeholder="备注" />
        <button type="submit">创建</button>
      </form>

      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>邀请码</th>
              <th>状态</th>
              <th>使用</th>
              <th>有效</th>
              <th>备注</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="invite in inviteCodes" :key="invite.id">
              <td><strong class="code-text">{{ invite.code }}</strong></td>
              <td><span class="status-pill" :class="invite.is_enabled ? 'ok' : 'danger'">{{ invite.is_enabled ? '启用' : '禁用' }}</span></td>
              <td>{{ invite.used_count }} / {{ invite.max_uses || '不限' }}</td>
              <td><span class="status-pill" :class="invite.is_valid ? 'ok' : 'warn'">{{ invite.is_valid ? '是' : '否' }}</span></td>
              <td>{{ invite.note || '-' }}</td>
              <td>
                <button @click="toggleInvite(invite)">{{ invite.is_enabled ? '禁用' : '启用' }}</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="activeTab === 'competitions'" class="admin-section">
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>比赛</th>
              <th>邀请码</th>
              <th>状态</th>
              <th>题目</th>
              <th>答案/WP/备注</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="competition in competitions" :key="competition.id">
              <td>{{ competition.name }}</td>
              <td><span class="code-text">{{ competition.code }}</span></td>
              <td>
                <span class="status-pill" :class="competition.is_archived ? 'warn' : 'ok'">
                  {{ competition.is_archived ? '已归档' : '进行中' }}
                </span>
              </td>
              <td>{{ competition.task_count }}</td>
              <td>{{ competition.answer_count }} / {{ competition.writeup_count }} / {{ competition.note_count }}</td>
              <td>
                <button @click="toggleCompetitionArchive(competition)">
                  {{ competition.is_archived ? '取消归档' : '归档' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="activeTab === 'storage'" class="admin-section">
      <div class="metric-grid compact">
        <div class="metric"><span>附件总数</span><strong>{{ storage.total_files || 0 }}</strong></div>
        <div class="metric"><span>附件大小</span><strong>{{ formatBytes(storage.total_bytes) }}</strong></div>
        <div class="metric"><span>孤立附件</span><strong>{{ storage.orphan_files || 0 }}</strong></div>
        <div class="metric"><span>孤立大小</span><strong>{{ formatBytes(storage.orphan_bytes) }}</strong></div>
      </div>

      <div class="section-actions">
        <button :disabled="!storage.orphan_files" @click="deleteOrphans">清理孤立附件</button>
      </div>

      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>文件名</th>
              <th>大小</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="file in storage.files" :key="file.filename">
              <td class="file-cell">{{ file.filename }}</td>
              <td>{{ formatBytes(file.size) }}</td>
              <td>
                <span class="status-pill" :class="file.is_orphan ? 'danger' : 'ok'">
                  {{ file.is_orphan ? '孤立' : '已引用' }}
                </span>
              </td>
              <td>
                <a class="table-link" :href="storageDownloadUrl(file)" download>下载附件</a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="activeTab === 'backup'" class="admin-section backup-panel">
      <p class="page-kicker">DATABASE BACKUP</p>
      <h3>数据库备份</h3>
      <p>下载当前 SQLite 数据库文件。恢复前请先确认文件版本，避免覆盖现场数据。</p>
      <a class="download-link" :href="backupUrl" download>下载数据库备份</a>
    </section>

    <section v-if="activeTab === 'settings'" class="admin-section settings-grid">
      <label>
        <span>开放注册</span>
        <select v-model="settings.registration_enabled">
          <option value="true">true</option>
          <option value="false">false</option>
        </select>
      </label>
      <label>
        <span>默认注册角色</span>
        <select v-model="settings.default_user_role">
          <option value="member">member</option>
          <option value="admin">admin</option>
        </select>
      </label>
      <label>
        <span>上传上限 MB</span>
        <input v-model="settings.max_upload_mb" type="number" min="1" />
      </label>
      <label>
        <span>会话有效期 小时</span>
        <input v-model="settings.session_timeout_hours" type="number" min="1" max="720" />
      </label>
      <label>
        <span>普通用户创建比赛</span>
        <select v-model="settings.allow_member_create_competition">
          <option value="true">true</option>
          <option value="false">false</option>
        </select>
      </label>
      <label class="wide">
        <span>系统公告</span>
        <input v-model="settings.system_announcement" type="text" />
      </label>
      <button @click="saveSettings">保存配置</button>
    </section>

    <section v-if="activeTab === 'logs'" class="admin-section">
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>时间</th>
              <th>用户</th>
              <th>动作</th>
              <th>目标</th>
              <th>IP</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="log in auditLogs" :key="log.id">
              <td>{{ formatDate(log.created_at) }}</td>
              <td>{{ log.actor || '-' }}</td>
              <td>{{ log.action }}</td>
              <td>{{ log.target_type || '-' }} {{ log.target_id || '' }}</td>
              <td>{{ log.ip_address || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.admin-console {
  padding: 1rem 0 2rem;
}

.admin-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.5rem;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background:
    linear-gradient(90deg, rgba(74, 200, 206, 0.12), transparent 46%),
    repeating-linear-gradient(135deg, rgba(255, 255, 255, 0.025) 0 1px, transparent 1px 16px),
    var(--bg-panel);
  box-shadow: 0 22px 70px rgba(0, 0, 0, 0.24);
}

.admin-hero h2 {
  margin: 0;
  color: var(--text-main);
  font-family: var(--font-mono);
  font-size: clamp(1.8rem, 4vw, 3rem);
  line-height: 1.1;
}

.admin-hero p:not(.page-kicker),
.backup-panel p {
  margin: 0.45rem 0 0;
  color: var(--text-muted);
}

.hero-actions,
.section-actions,
.actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: center;
}

.backup-mini {
  min-height: 38px;
}

.tab-row {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  padding: 0.35rem;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-card);
}

.tab-button {
  background: transparent;
  font-family: var(--font-mono);
  color: var(--text-muted);
}

.tab-button.active {
  color: var(--accent-cyan);
  border-color: var(--accent-cyan);
  background: rgba(74, 200, 206, 0.1);
  box-shadow: 0 0 14px var(--accent-cyan-glow);
}

.admin-section {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 1.25rem;
  overflow-x: auto;
  box-shadow: 0 16px 45px rgba(0, 0, 0, 0.2);
}

.section-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.section-head h3,
.backup-panel h3 {
  margin: 0;
  color: var(--text-main);
  font-family: var(--font-mono);
  font-size: 1.25rem;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 0.85rem;
}

.metric-grid.compact {
  margin-bottom: 1rem;
}

.metric {
  background:
    linear-gradient(180deg, rgba(74, 200, 206, 0.06), transparent),
    var(--bg-main);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.metric span,
.settings-grid span {
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 0.82rem;
}

.metric strong {
  color: var(--text-main);
  font-size: 1.46rem;
  font-family: var(--font-mono);
}

.inline-form,
.password-form {
  display: grid;
  grid-template-columns: 1fr 140px 1fr auto;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.password-form {
  grid-template-columns: 1fr 1fr auto;
  padding: 1rem;
  border: 1px dashed var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-main);
}

.actions input {
  width: 150px;
}

.self-chip {
  display: inline-flex;
  margin-left: 8px;
  padding: 2px 6px;
  border: 1px solid rgba(241, 189, 97, 0.35);
  border-radius: 4px;
  color: var(--accent-amber);
  font-family: var(--font-mono);
  font-size: 0.7rem;
}

.self-note {
  display: block;
  margin-top: 0.4rem;
  color: var(--accent-amber);
  font-size: 0.78rem;
  font-family: var(--font-mono);
}

.section-actions {
  margin-bottom: 1rem;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(220px, 1fr));
  gap: 1rem;
}

.settings-grid label {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.settings-grid .wide {
  grid-column: 1 / -1;
}

.settings-grid button {
  width: fit-content;
}

.table-scroll {
  width: 100%;
  overflow-x: auto;
}

.table-scroll table {
  min-width: 880px;
}

.code-text,
.file-cell {
  font-family: var(--font-mono);
  word-break: break-all;
}

.code-text {
  color: var(--accent-amber);
}

@media (max-width: 860px) {
  .admin-hero,
  .section-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .inline-form,
  .password-form,
  .settings-grid {
    grid-template-columns: 1fr;
  }
}
</style>
