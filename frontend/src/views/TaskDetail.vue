<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { api, API_BASE, resolveApiUrl } from '../api'

const route = useRoute()
const token = ref(localStorage.getItem('token') || '')
const username = ref(localStorage.getItem('username') || '')

const taskId = route.params.id
const task = ref(null)
const loading = ref(true)
let eventSource = null

const inputs = ref({ answer: '', wp: '', note: '' })
const fileInput = ref(null)
const editing = ref({ type: '', id: null, content: '' })

const fetchTask = async (showLoading = true) => {
  if (showLoading) loading.value = true
  try {
    const res = await api.get(`/api/tasks/${taskId}`, {
      headers: { Authorization: `Bearer ${token.value}` }
    })
    task.value = res.data
  } catch (error) {
    console.error(error)
    if (error.response?.status === 401) {
      alert('登录已过期，请重新登录')
      localStorage.removeItem('token')
      window.location.href = '/'
    }
  } finally {
    if (showLoading) loading.value = false
  }
}

const setupSSE = () => {
  if (eventSource) return;
  eventSource = new EventSource(`${API_BASE}/api/stream`)
  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.action === 'refresh' && (!data.task_id || data.task_id === taskId)) {
      fetchTask(false) // Fetch silently
    }
  }
}

onMounted(() => {
  fetchTask()
  setupSSE()
})

onUnmounted(() => {
  if (eventSource) {
    eventSource.close()
  }
})

const handleFileChange = (e) => {
  if (e.target.files.length > 0) {
    fileInput.value = e.target.files[0]
  } else {
    fileInput.value = null
  }
}

const handleAdd = async (type) => {
  const content = inputs.value[type]
  const file = type === 'wp' ? fileInput.value : null
  
  if (!content && !file) return

  try {
    let res;
    if (type === 'wp' && file) {
      const formData = new FormData()
      formData.append('content', content || '')
      formData.append('file', file)
      res = await api.post(`/api/tasks/${taskId}/${type}`, formData, {
        headers: { 
          'Content-Type': 'multipart/form-data',
          Authorization: `Bearer ${token.value}` 
        }
      })
    } else {
      res = await api.post(`/api/tasks/${taskId}/${type}`, { content }, {
        headers: { Authorization: `Bearer ${token.value}` }
      })
    }
    
    // Refresh locally
    if (type === 'answer') {
      if (res.data.is_new) {
        task.value.answers.push({ id: res.data.id, user: res.data.user, content })
      } else {
        const existing = task.value.answers.find(a => a.user === res.data.user)
        if (existing) existing.content = content
      }
    }
    if (type === 'wp') {
      task.value.wps.push({ 
        id: res.data.id, 
        user: res.data.user, 
        content,
        file_url: res.data.file_url,
        file_type: res.data.file_type,
        original_filename: res.data.original_filename
      })
      // Clear file input
      fileInput.value = null
      const fileInputEl = document.getElementById('wp_file')
      if (fileInputEl) fileInputEl.value = ''
    }
    if (type === 'note') task.value.notes.push({ id: res.data.id, user: res.data.user, content })
    
    inputs.value[type] = ''
  } catch (error) {
    alert(error.response?.data?.error || '添加失败')
  }
}

const startEdit = (type, item) => {
  editing.value = { type, id: item.id, content: item.content }
}

const cancelEdit = () => {
  editing.value = { type: '', id: null, content: '' }
}

const saveEdit = async () => {
  const { type, id, content } = editing.value
  if (!content.trim()) return

  try {
    await api.put(`/api/items/${type}/${id}`, { content }, {
      headers: { Authorization: `Bearer ${token.value}` }
    })
    
    let list = []
    if (type === 'answer') list = task.value.answers
    else if (type === 'wp') list = task.value.wps
    else if (type === 'note') list = task.value.notes
    
    const item = list.find(i => i.id === id)
    if (item) item.content = content
    
    cancelEdit()
  } catch (error) {
    alert(error.response?.data?.error || '修改失败')
  }
}

const handleDelete = async (type, id) => {
  if (!confirm('确定要删除这条内容吗？如果是WP，附带的文件也会被删除。')) return

  try {
    await api.delete(`/api/items/${type}/${id}`, {
      headers: { Authorization: `Bearer ${token.value}` }
    })
    
    if (type === 'answer') {
      task.value.answers = task.value.answers.filter(a => a.id !== id)
    } else if (type === 'wp') {
      task.value.wps = task.value.wps.filter(w => w.id !== id)
    } else if (type === 'note') {
      task.value.notes = task.value.notes.filter(n => n.id !== id)
    }
  } catch (error) {
    alert(error.response?.data?.error || '删除失败')
  }
}
</script>

<template>
  <div class="task-detail-container">
    <div class="back-link-wrapper">
      <router-link to="/competitions" class="back-link">&larr; 返回题目列表</router-link>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      加载数据中...
    </div>
    <div v-else-if="!task" class="error-state">未找到该题目</div>
    <div v-else>
      <div class="task-header-card">
        <h2 class="task-title">
          <span>题目详情</span>
          <div class="code-badge">
            <span class="label">唯一编码:</span>
            <strong class="value">{{ task.code || task.id }}</strong>
          </div>
        </h2>
        <div class="task-content-section">
          <h4 class="section-label">题目内容：</h4>
          <p class="task-content-text">{{ task.content }}</p>
        </div>
      </div>

      <!-- Collaboration Panels -->
      <div class="panels-grid">
        
        <!-- Answers -->
        <div class="panel-card answer-panel">
          <h3 class="panel-title answer-title">答案区</h3>
          <div class="items-list">
            <div v-for="item in task.answers" :key="item.id" class="item-row">
              <div class="item-header">
                <span class="item-user answer-user">{{ item.user }}: </span>
                <div v-if="(item.user === username || username === 'admin') && editing.id !== item.id" class="item-actions">
                  <button @click="startEdit('answer', item)" class="btn-text">修改</button>
                  <button @click="handleDelete('answer', item.id)" class="btn-text danger">删除</button>
                </div>
              </div>

              <div v-if="editing.type === 'answer' && editing.id === item.id" class="edit-box">
                <textarea v-model="editing.content" class="edit-textarea answer-textarea" rows="2"></textarea>
                <div class="edit-actions">
                  <button @click="cancelEdit" class="btn-cancel">取消</button>
                  <button @click="saveEdit" class="btn-save answer-btn">保存</button>
                </div>
              </div>
              <span v-else class="item-content">{{ item.content }}</span>
            </div>
            <div v-if="task.answers.length === 0" class="empty-text">暂无答案数据...</div>
          </div>
          <div v-if="!task.answers.some(a => a.user === username)" class="input-group">
            <input type="text" v-model="inputs.answer" :placeholder="`${username}: 输入答案...`" class="main-input" @keyup.enter="handleAdd('answer')" />
            <button @click="handleAdd('answer')" class="btn-submit answer-btn">提交</button>
          </div>
        </div>

        <!-- WPs -->
        <div class="panel-card wp-panel">
          <h3 class="panel-title wp-title">Writeups区</h3>
          <div class="items-list">
            <div v-for="item in task.wps" :key="item.id" class="item-row">
              <div class="item-header">
                <div class="item-user wp-user">{{ item.user }}:</div>
                <div v-if="(item.user === username || username === 'admin') && editing.id !== item.id" class="item-actions">
                  <button @click="startEdit('wp', item)" class="btn-text">修改</button>
                  <button @click="handleDelete('wp', item.id)" class="btn-text danger">删除</button>
                </div>
              </div>

              <div v-if="editing.type === 'wp' && editing.id === item.id" class="edit-box">
                <textarea v-model="editing.content" class="edit-textarea wp-textarea" rows="3"></textarea>
                <div class="edit-actions">
                  <button @click="cancelEdit" class="btn-cancel">取消</button>
                  <button @click="saveEdit" class="btn-save wp-btn">保存</button>
                </div>
              </div>
              <div v-else-if="item.content" class="item-content" style="margin-bottom: 8px;">{{ item.content }}</div>

              <div v-if="item.file_url" class="file-preview">
                <div v-if="item.original_filename" class="file-name">文件：{{ item.original_filename }}</div>
                <img v-if="item.file_type === 'image'" :src="resolveApiUrl(item.file_url)" class="image-preview" />
                <a :href="resolveApiUrl(item.file_url)" target="_blank" download class="download-link">下载附件</a>
              </div>
            </div>
            <div v-if="task.wps.length === 0" class="empty-text">暂无 WP 数据...</div>
          </div>
          <div class="input-group-col">
            <textarea v-model="inputs.wp" :placeholder="`${username}: 输入WP...`" rows="2" class="main-textarea"></textarea>
            <div class="file-upload-row">
              <input type="file" id="wp_file" @change="handleFileChange" class="file-input" />
              <button @click="handleAdd('wp')" class="btn-submit wp-btn">提交 WP</button>
            </div>
          </div>
        </div>

        <!-- Notes -->
        <div class="panel-card note-panel">
          <h3 class="panel-title note-title">备注区</h3>
          <div class="items-list">
            <div v-for="item in task.notes" :key="item.id" class="item-row">
              <div class="item-header">
                <span class="item-user note-user">{{ item.user }}: </span>
                <div v-if="(item.user === username || username === 'admin') && editing.id !== item.id" class="item-actions">
                  <button @click="startEdit('note', item)" class="btn-text">修改</button>
                  <button @click="handleDelete('note', item.id)" class="btn-text danger">删除</button>
                </div>
              </div>

              <div v-if="editing.type === 'note' && editing.id === item.id" class="edit-box">
                <textarea v-model="editing.content" class="edit-textarea note-textarea" rows="2"></textarea>
                <div class="edit-actions">
                  <button @click="cancelEdit" class="btn-cancel">取消</button>
                  <button @click="saveEdit" class="btn-save note-btn">保存</button>
                </div>
              </div>
              <span v-else class="item-content">{{ item.content }}</span>
            </div>
            <div v-if="task.notes.length === 0" class="empty-text">暂无备注数据...</div>
          </div>
          <div class="input-group">
            <input type="text" v-model="inputs.note" :placeholder="`${username}: 输入备注...`" class="main-input" @keyup.enter="handleAdd('note')" />
            <button @click="handleAdd('note')" class="btn-submit note-btn">提交</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.task-detail-container {
  width: 100%;
  box-sizing: border-box;
  padding: 1rem 0;
}

.back-link-wrapper {
  margin-bottom: 2rem;
}

.back-link {
  text-decoration: none;
  color: var(--accent-cyan);
  font-family: var(--font-mono);
  font-weight: bold;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  opacity: 0.8;
  display: inline-block;
}

.back-link:hover {
  opacity: 1;
  text-shadow: 0 0 10px var(--accent-cyan-glow);
  transform: translateX(-4px);
}

.loading-state, .error-state {
  font-family: var(--font-mono);
  text-align: center;
  padding: 4rem;
}

.loading-state {
  color: var(--text-muted);
}

.error-state {
  color: var(--accent-danger);
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(0, 229, 255, 0.1);
  border-top-color: var(--accent-cyan);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.task-header-card {
  border: 1px solid var(--border-subtle);
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 2rem;
  background:
    linear-gradient(90deg, rgba(74, 200, 206, 0.09), transparent),
    var(--bg-card);
  box-shadow: 0 16px 45px rgba(0,0,0,0.2);
  transition: all 0.3s ease;
}

.task-header-card:hover {
  border-color: var(--border-focus);
  box-shadow: 0 8px 30px rgba(0,0,0,0.2), 0 0 15px var(--accent-cyan-glow);
}

.task-title {
  margin-top: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-family: var(--font-mono);
  color: var(--accent-cyan);
  padding-bottom: 1rem;
  border-bottom: 1px dashed var(--border-subtle);
  margin-bottom: 1.5rem;
}

.code-badge {
  font-size: 0.85em;
  background: var(--bg-main);
  padding: 8px 16px;
  border-radius: 6px;
  border-left: 3px solid var(--accent-amber);
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
  display: flex;
  align-items: center;
  gap: 8px;
  text-shadow: none;
}

.code-badge .label {
  color: var(--text-muted);
  font-weight: normal;
  text-transform: uppercase;
}

.code-badge .value {
  color: var(--accent-amber);
  letter-spacing: 1.5px;
}

.task-content-section {
  margin-bottom: 0.5rem;
}

.section-label {
  margin: 0 0 0.8rem 0;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.task-content-text {
  white-space: pre-wrap;
  margin: 0;
  font-size: 1.1em;
  color: var(--text-main);
  background: var(--bg-panel);
  padding: 1.5rem;
  border-radius: 6px;
  border: 1px dashed var(--border-subtle);
  line-height: 1.7;
}

.panels-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 2rem;
}

.panel-card {
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 1.35rem;
  background: var(--bg-panel);
  box-shadow: 0 14px 34px rgba(0,0,0,0.16);
  display: flex;
  flex-direction: column;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.panel-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 25px rgba(0,0,0,0.15);
}

.panel-title {
  border-bottom: 1px solid;
  padding-bottom: 1rem;
  margin-top: 0;
  font-family: var(--font-mono);
  font-size: 1.4rem;
}

.answer-title { border-color: var(--accent-cyan); color: var(--accent-cyan); }
.wp-title { border-color: var(--accent-green); color: var(--accent-green); }
.note-title { border-color: var(--accent-amber); color: var(--accent-amber); }

.items-list {
  flex: 1;
  max-height: 400px;
  overflow-y: auto;
  margin-bottom: 1.5rem;
  padding-right: 0.5rem;
}

.item-row {
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px dashed var(--border-subtle);
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 6px;
}

.item-user { font-weight: bold; }
.answer-user { color: var(--accent-cyan); }
.wp-user { color: var(--accent-green); }
.note-user { color: var(--accent-amber); }

.item-actions {
  display: flex;
  gap: 12px;
}

.btn-text {
  background: none;
  border: none;
  color: var(--text-muted);
  padding: 0;
  font-size: 0.85em;
  cursor: pointer;
  box-shadow: none;
  transition: color 0.2s;
}

.btn-text:hover { color: var(--text-main); }
.btn-text.danger:hover { color: var(--accent-danger); }

.edit-box {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.edit-textarea {
  width: 100%;
  box-sizing: border-box;
  padding: 10px;
  border-radius: 6px;
  background: var(--bg-main);
  color: var(--text-main);
  font-family: var(--font-sans);
  resize: vertical;
}

.answer-textarea { border: 1px solid var(--accent-cyan); }
.wp-textarea { border: 1px solid var(--accent-green); }
.note-textarea { border: 1px solid var(--accent-amber); }

.edit-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.btn-cancel {
  background: transparent;
  color: var(--text-muted);
  padding: 6px 14px;
  font-size: 0.85em;
  border: 1px solid var(--border-subtle);
  box-shadow: none;
}

.btn-save {
  padding: 6px 14px;
  font-size: 0.85em;
  box-shadow: none;
}

.item-content {
  white-space: pre-wrap;
  display: block;
  margin-top: 4px;
  color: var(--text-main);
  line-height: 1.6;
}

.empty-text {
  color: var(--text-muted);
  font-size: 0.9em;
  font-family: var(--font-mono);
  text-align: center;
  padding: 2rem 0;
}

.input-group {
  display: flex;
  gap: 10px;
  border-top: 1px dashed var(--border-subtle);
  padding-top: 1.5rem;
}

.input-group-col {
  display: flex;
  flex-direction: column;
  gap: 12px;
  border-top: 1px dashed var(--border-subtle);
  padding-top: 1.5rem;
}

.main-input, .main-textarea {
  flex: 1;
  padding: 12px 16px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-main);
  color: var(--text-main);
  font-family: var(--font-sans);
  transition: all 0.3s;
}

.main-textarea {
  resize: vertical;
}

.file-upload-row {
  display: flex;
  gap: 12px;
  align-items: center;
}

.file-input {
  flex: 1;
  font-size: 0.85em;
}

.btn-submit {
  padding: 10px 24px;
  border-radius: 8px;
  font-weight: bold;
  white-space: nowrap;
}

.answer-btn { background: rgba(74, 200, 206, 0.1); color: var(--accent-cyan); border: 1px solid var(--accent-cyan); }
.answer-btn:hover { background: rgba(74, 200, 206, 0.18); box-shadow: 0 0 15px var(--accent-cyan-glow); }

.wp-btn { background: rgba(123, 216, 137, 0.1); color: var(--accent-green); border: 1px solid var(--accent-green); }
.wp-btn:hover { background: rgba(123, 216, 137, 0.18); box-shadow: 0 0 15px rgba(123, 216, 137, 0.24); }

.note-btn { background: rgba(241, 189, 97, 0.1); color: var(--accent-amber); border: 1px solid var(--accent-amber); }
.note-btn:hover { background: rgba(241, 189, 97, 0.18); box-shadow: 0 0 15px rgba(241, 189, 97, 0.22); }

.file-preview {
  margin-top: 12px;
  background: rgba(0,0,0,0.1);
  padding: 12px;
  border-radius: 6px;
  border: 1px solid var(--border-subtle);
}

.file-name {
  font-size: 0.85em;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.image-preview {
  max-width: 100%;
  max-height: 250px;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.download-link {
  margin-top: 8px;
}
</style>
