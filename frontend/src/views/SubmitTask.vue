<script setup>
import { ref, onMounted } from 'vue'
import UploadExcel from '../components/UploadExcel.vue'
import { api } from '../api'

const token = ref(localStorage.getItem('token') || '')

const form = ref({
  competition_id: '',
  content: ''
})
const result = ref(null)
const errorMsg = ref('')
const competitions = ref([])

const fetchCompetitions = async () => {
  try {
    const res = await api.get('/api/competitions', {
      headers: { Authorization: `Bearer ${token.value}` }
    })
    competitions.value = res.data
  } catch (error) {
    console.error(error)
  }
}

onMounted(() => {
  fetchCompetitions()
})

const handleSubmit = async () => {
  errorMsg.value = ''
  result.value = null
  if (!form.value.competition_id) {
    errorMsg.value = '请先选择所属比赛'
    return
  }
  try {
    const res = await api.post('/api/tasks/single', form.value, {
      headers: { Authorization: `Bearer ${token.value}` }
    })
    result.value = res.data
    form.value.content = ''
  } catch (error) {
    errorMsg.value = error.response?.data?.error || '提交失败'
  }
}
</script>

<template>
  <div class="submit-container page-shell">
    <div class="page-header">
      <div>
        <p class="page-kicker">DATA INTAKE</p>
        <h2 class="page-title">题目上传</h2>
        <p class="page-subtitle">将单题或 Excel 题库接入指定比赛行动。</p>
      </div>
    </div>

    <div class="submit-layout">
      <div class="submit-card">
        <div class="card-heading">
          <span class="section-code">MANUAL</span>
          <h3 class="card-title">手动上传单道题目</h3>
        </div>
        <form @submit.prevent="handleSubmit" class="submit-form">
          <div class="form-group">
            <label class="form-label">选择目标题目组</label>
            <select v-model="form.competition_id" required class="form-select">
              <option value="" disabled>-- 请选择目标题目组 --</option>
              <option v-for="comp in competitions" :key="comp.id" :value="comp.id">{{ comp.name }} ({{ comp.code }})</option>
            </select>
            <span v-if="competitions.length === 0" class="warning-badge">无可用题目组，请先建立比赛。</span>
          </div>
          <div class="form-group">
            <label class="form-label">题目内容</label>
            <textarea v-model="form.content" rows="4" required class="form-textarea"></textarea>
          </div>
          <button type="submit" class="btn-submit">确认上传</button>
        </form>

        <div v-if="errorMsg" class="state-message error">错误: {{ errorMsg }}</div>

        <div v-if="result" class="success-panel">
          <h4 class="success-title">上传成功</h4>
          <router-link :to="`/tasks/${result.id}`" class="success-link">前往题目详情页</router-link>
        </div>
      </div>

      <UploadExcel :token="token" />
    </div>
  </div>
</template>

<style scoped>
.submit-container {
  width: 100%;
  padding: 1rem 0;
}

.submit-layout {
  display: grid;
  grid-template-columns: minmax(320px, 0.95fr) minmax(320px, 1.05fr);
  gap: 1rem;
  align-items: start;
}

.submit-card {
  border: 1px solid var(--border-subtle);
  padding: 1.5rem;
  border-radius: 8px;
  background: var(--bg-card);
  box-shadow: 0 16px 45px rgba(0, 0, 0, 0.2);
  transition: all 0.25s ease;
}

.submit-card:hover {
  border-color: var(--border-focus);
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.26), 0 0 18px var(--accent-cyan-glow);
}

.card-heading {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin-bottom: 1.4rem;
}

.section-code {
  color: var(--accent-amber);
  font-family: var(--font-mono);
  font-size: 0.76rem;
  letter-spacing: 0.16em;
}

.card-title {
  margin: 0;
  color: var(--text-main);
  font-family: var(--font-mono);
  font-size: 1.35rem;
  font-weight: 800;
}

.submit-form {
  display: flex;
  flex-direction: column;
  gap: 1.4rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.form-label {
  font-weight: 700;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 0.88rem;
}

.form-select,
.form-textarea {
  font-size: 1rem;
}

.warning-badge {
  color: var(--accent-danger);
  font-size: 0.84em;
  font-family: var(--font-mono);
  display: inline-block;
  background: rgba(255, 111, 97, 0.1);
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid rgba(255, 111, 97, 0.24);
}

.btn-submit {
  width: fit-content;
  padding: 0.82rem 1.6rem;
  font-family: var(--font-mono);
  background: rgba(74, 200, 206, 0.12);
  border: 1px solid var(--accent-cyan);
  color: var(--accent-cyan);
  font-weight: 800;
}

.state-message {
  margin-top: 1rem;
}

.success-panel {
  margin-top: 1.5rem;
  padding: 1.1rem;
  background-color: var(--final-answer-bg);
  border: 1px solid var(--final-answer-border);
  border-radius: 8px;
}

.success-title {
  margin: 0 0 0.5rem;
  color: var(--accent-green);
  font-family: var(--font-mono);
  font-size: 1.05rem;
}

.success-link {
  color: var(--accent-cyan);
  text-decoration: none;
  font-weight: bold;
  font-family: var(--font-mono);
}

.success-link::after {
  content: " >";
  color: var(--accent-amber);
}

@media (max-width: 980px) {
  .submit-layout {
    grid-template-columns: 1fr;
  }
}
</style>
