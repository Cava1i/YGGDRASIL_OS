<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'

const props = defineProps(['token'])
const file = ref(null)
const message = ref('')
const competitions = ref([])
const selectedCompId = ref('')

const fetchCompetitions = async () => {
  try {
    const res = await api.get('/api/competitions', {
      headers: { Authorization: `Bearer ${props.token}` }
    })
    competitions.value = res.data
  } catch (error) {
    console.error(error)
  }
}

onMounted(() => {
  fetchCompetitions()
})

const handleFileChange = (e) => {
  file.value = e.target.files[0]
}

const handleUpload = async () => {
  if (!selectedCompId.value) {
    message.value = '请先选择所属比赛'
    return
  }
  if (!file.value) {
    message.value = '请先选择文件'
    return
  }

  const formData = new FormData()
  formData.append('file', file.value)
  formData.append('competition_id', selectedCompId.value)

  try {
    const res = await api.post('/api/tasks/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
        'Authorization': `Bearer ${props.token}`
      }
    })
    message.value = res.data.message
    setTimeout(() => {
      window.location.href = `/competitions/${selectedCompId.value}`
    }, 1000)
  } catch (error) {
    message.value = error.response?.data?.error || '上传失败'
  }
}
</script>

<template>
  <div class="upload-card">
    <div class="card-heading">
      <span class="section-code">BATCH</span>
      <h3 class="card-title">批量上传 (Excel)</h3>
    </div>
    <p class="helper-text">
      请上传包含题目的 Excel 文件。<br>
      格式要求至少包含2列：题目ID、题目内容。
    </p>
    
    <div class="form-container">
      <div class="form-group">
        <label class="form-label">选择目标题目组 (必选)</label>
        <select v-model="selectedCompId" class="form-select">
          <option value="" disabled>-- 请选择目标题目组 --</option>
          <option v-for="comp in competitions" :key="comp.id" :value="comp.id">{{ comp.name }} ({{ comp.code }})</option>
        </select>
        <span v-if="competitions.length === 0" class="warning-badge">错误: 无可用题目组，请先去控制中心建立！</span>
      </div>

      <div class="form-group">
        <label class="form-label">上传 Excel 数据文件</label>
        <div class="upload-row">
          <input type="file" accept=".xlsx, .xls, .csv" @change="handleFileChange" class="file-input" />
          <button @click="handleUpload" class="btn-upload">
            上传并导入
          </button>
        </div>
      </div>
      
      <div v-if="message" class="message-badge" :class="{'is-error': message.includes('失败') || message.includes('请先') || message.includes('错误')}">
        {{ message }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.upload-card {
  padding: 1.5rem;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-card);
  box-shadow: 0 16px 45px rgba(0, 0, 0, 0.2);
  transition: all 0.3s ease;
}

.upload-card:hover {
  border-color: var(--border-focus);
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.26), 0 0 18px rgba(123, 216, 137, 0.16);
}

.card-heading {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin-bottom: 1rem;
}

.section-code {
  color: var(--accent-amber);
  font-family: var(--font-mono);
  font-size: 0.76rem;
  letter-spacing: 0.16em;
}

.card-title {
  margin: 0;
  color: var(--accent-green);
  font-family: var(--font-mono);
  font-size: 1.35rem;
  font-weight: 800;
}

.helper-text {
  color: var(--text-muted);
  font-size: 0.95rem;
  font-family: var(--font-mono);
  border-left: 3px solid var(--accent-green);
  padding-left: 15px;
  line-height: 1.6;
  background: var(--bg-main);
  padding-top: 10px;
  padding-bottom: 10px;
  border-radius: 0 6px 6px 0;
}

.form-container {
  margin-top: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.35rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.form-label {
  font-weight: 600;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 0.95rem;
}

.form-select {
  width: 100%;
  padding: 1rem 1.2rem;
  font-size: 1rem;
  background: var(--bg-main);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  color: var(--text-main);
  font-family: var(--font-sans);
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.form-select:hover {
  border-color: rgba(123, 216, 137, 0.4);
}

.form-select:focus {
  outline: none;
  border-color: var(--accent-green);
  box-shadow: 0 0 0 3px rgba(123, 216, 137, 0.1);
  background-color: var(--bg-card);
}

.warning-badge {
  color: var(--accent-danger);
  font-size: 0.85em;
  font-family: var(--font-mono);
  background: rgba(255, 111, 97, 0.1);
  padding: 6px 12px;
  border-radius: 6px;
  display: inline-block;
  margin-top: 5px;
  border: 1px solid rgba(255, 111, 97, 0.24);
}

.upload-row {
  display: flex;
  gap: 1rem;
  align-items: stretch;
}

.file-input {
  flex: 1;
  padding: 0.8rem;
  background: var(--bg-main);
  border-radius: 8px;
}

.btn-upload {
  white-space: nowrap;
  background: rgba(123, 216, 137, 0.1);
  border: 1px solid var(--accent-green);
  color: var(--accent-green);
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  font-family: var(--font-mono);
  font-size: 1.05rem;
  padding: 0 2rem;
  border-radius: 8px;
  font-weight: bold;
  cursor: pointer;
}

.btn-upload:hover {
  background: rgba(123, 216, 137, 0.18);
  box-shadow: 0 4px 15px rgba(123, 216, 137, 0.22);
  transform: translateY(-2px);
}

.message-badge {
  color: var(--accent-green);
  font-weight: bold;
  font-family: var(--font-mono);
  margin-top: -0.5rem;
  background: rgba(123, 216, 137, 0.1);
  padding: 10px 15px;
  border-radius: 6px;
  border: 1px solid rgba(123, 216, 137, 0.24);
}

.message-badge.is-error {
  color: var(--accent-danger);
  background: rgba(255, 111, 97, 0.1);
  border-color: rgba(255, 111, 97, 0.24);
}

@media (max-width: 680px) {
  .upload-row {
    flex-direction: column;
  }

  .btn-upload {
    min-height: 44px;
  }
}
</style>
