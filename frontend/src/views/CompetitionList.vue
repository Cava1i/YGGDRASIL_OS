<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'

const router = useRouter()
const token = ref(localStorage.getItem('token') || '')
const competitions = ref([])
const loading = ref(true)

const showCreateModal = ref(false)
const newCompName = ref('')
const createError = ref('')

const fetchCompetitions = async () => {
  try {
    const res = await api.get('/api/competitions', {
      headers: { Authorization: `Bearer ${token.value}` }
    })
    competitions.value = res.data
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchCompetitions()
})

const handleCreate = async () => {
  createError.value = ''
  if (!newCompName.value.trim()) return

  try {
    await api.post('/api/competitions',
      { name: newCompName.value },
      { headers: { Authorization: `Bearer ${token.value}` } }
    )
    showCreateModal.value = false
    newCompName.value = ''
    fetchCompetitions()
  } catch (error) {
    createError.value = error.response?.data?.error || '创建失败'
  }
}

const goToDetail = (id) => {
  router.push(`/competitions/${id}`)
}

const deleteCompetition = async (id, name, event) => {
  event.stopPropagation()
  if (!confirm(`确定要删除比赛 "${name}" 吗？此操作不可恢复，所有相关题目和解答都会被删除！`)) return

  try {
    await api.delete(`/api/competitions/${id}`, {
      headers: { Authorization: `Bearer ${token.value}` }
    })
    fetchCompetitions()
  } catch (error) {
    alert(error.response?.data?.error || '删除失败')
  }
}
</script>

<template>
  <div class="comp-container page-shell">
    <div class="page-header">
      <div>
        <p class="page-kicker">OPERATIONS</p>
        <h2 class="page-title">比赛行动</h2>
        <p class="page-subtitle">按比赛组织题目、答案、WP 和备注，保持团队分析进度在同一张作战图上。</p>
      </div>
      <button @click="showCreateModal = true" class="btn-primary create-button">
        <span>+</span> 新建比赛
      </button>
    </div>

    <div v-if="showCreateModal" class="modal-overlay">
      <div class="modal-content">
        <p class="page-kicker">NEW OPERATION</p>
        <h3 class="modal-title">新建比赛</h3>
        <input
          v-model="newCompName"
          type="text"
          placeholder="输入比赛名称..."
          class="modal-input"
          @keyup.enter="handleCreate"
        />
        <p v-if="createError" class="error-msg">{{ createError }}</p>
        <div class="modal-actions">
          <button @click="showCreateModal = false" class="btn-secondary">取消</button>
          <button @click="handleCreate" class="btn-primary">确认建立</button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading-state panel">
      <div class="spinner"></div>
      <p>加载数据中...</p>
    </div>

    <div v-else-if="competitions.length === 0" class="empty-state panel">
      <div class="empty-code">NO OPS</div>
      <p>暂无比赛行动。</p>
    </div>

    <div v-else class="comp-grid">
      <div
        v-for="comp in competitions"
        :key="comp.id"
        @click="goToDetail(comp.id)"
        class="comp-card"
      >
        <div class="card-header">
          <div>
            <span class="status-pill ok">进行中</span>
            <h3 class="comp-name">{{ comp.name }}</h3>
          </div>
          <button @click="deleteCompetition(comp.id, comp.name, $event)" class="btn-delete-comp" title="删除比赛">
            删除
          </button>
        </div>
        <div class="comp-code">
          <span class="label">比赛编码</span>
          <span class="value">{{ comp.code }}</span>
        </div>
        <div class="comp-footer">
          <span class="task-count">题目数量 {{ comp.task_count }}</span>
          <span class="date">{{ new Date(comp.created_at).toLocaleDateString() }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.comp-container {
  padding: 1rem 0;
}

.create-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.create-button span {
  color: var(--accent-amber);
  font-weight: 900;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(3, 8, 8, 0.72);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 1rem;
}

.modal-content {
  width: min(460px, 100%);
  background: var(--bg-card);
  padding: 1.6rem;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
  box-shadow: 0 22px 70px rgba(0, 0, 0, 0.52), 0 0 22px var(--accent-cyan-glow);
}

.modal-title {
  margin: 0 0 1.2rem;
  font-family: var(--font-mono);
  color: var(--text-main);
}

.modal-input {
  margin-bottom: 1rem;
  font-family: var(--font-mono);
}

.modal-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
}

.error-msg {
  color: var(--accent-danger);
  margin: 0 0 1rem;
  font-size: 0.88rem;
  font-family: var(--font-mono);
}

.empty-code {
  color: var(--accent-amber);
  font-family: var(--font-mono);
  font-size: 1.2rem;
  font-weight: 900;
  margin-bottom: 0.5rem;
}

.comp-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1rem;
}

.comp-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 1.25rem;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  position: relative;
  overflow: hidden;
  box-shadow: 0 14px 36px rgba(0, 0, 0, 0.18);
}

.comp-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  width: 3px;
  height: 100%;
  background: linear-gradient(to bottom, var(--accent-cyan), var(--accent-amber));
  transform: scaleY(0);
  transition: transform 0.3s ease;
  transform-origin: bottom;
}

.comp-card:hover {
  transform: translateY(-5px);
  background: var(--bg-card-hover);
  border-color: var(--accent-cyan);
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.34), 0 0 16px var(--accent-cyan-glow);
}

.comp-card:hover::before {
  transform: scaleY(1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1.2rem;
}

.comp-name {
  margin: 0.85rem 0 0;
  color: var(--text-main);
  font-size: 1.28rem;
  font-weight: 800;
  line-height: 1.25;
}

.comp-code {
  font-family: var(--font-mono);
  font-size: 0.9em;
  margin-bottom: 1.35rem;
  background: var(--bg-main);
  padding: 10px 12px;
  border-radius: 6px;
  border-left: 3px solid var(--accent-amber);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.comp-code .label {
  color: var(--text-muted);
  font-size: 0.82em;
}

.comp-code .value {
  color: var(--accent-amber);
  font-weight: 900;
  letter-spacing: 0.08em;
}

.comp-footer {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  font-size: 0.85em;
  color: var(--text-muted);
  border-top: 1px dashed var(--border-subtle);
  padding-top: 1rem;
  font-family: var(--font-mono);
}

.btn-delete-comp {
  min-height: 30px;
  padding: 4px 8px;
  background: rgba(255, 111, 97, 0.08);
  border-color: rgba(255, 111, 97, 0.3);
  color: var(--accent-danger);
  font-family: var(--font-mono);
  font-size: 0.76rem;
}
</style>
