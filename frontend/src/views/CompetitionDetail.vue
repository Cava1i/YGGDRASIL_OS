<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TaskBoard from '../components/TaskBoard.vue'
import { api } from '../api'

const route = useRoute()
const router = useRouter()
const token = ref(localStorage.getItem('token') || '')
const username = ref(localStorage.getItem('username') || '')

const compId = route.params.id
const competition = ref(null)
const loading = ref(true)

const fetchCompetition = async () => {
  try {
    const res = await api.get(`/api/competitions/${compId}`, {
      headers: { Authorization: `Bearer ${token.value}` }
    })
    competition.value = res.data
  } catch (error) {
    console.error(error)
    if (error.response?.status === 404) {
      alert('比赛不存在')
      router.push('/competitions')
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchCompetition()
})
</script>

<template>
  <div class="competition-detail page-shell">
    <router-link to="/competitions" class="back-link">返回比赛行动</router-link>

    <div v-if="loading" class="loading-state panel">
      <div class="spinner"></div>
      加载数据中...
    </div>
    <div v-else-if="!competition" class="error-state panel">加载失败</div>
    <div v-else class="detail-body">
      <section class="operation-header">
        <div>
          <p class="page-kicker">OPERATION BOARD</p>
          <h2>{{ competition.name }}</h2>
        </div>
        <div class="operation-code">
          <span>比赛编码</span>
          <strong>{{ competition.code }}</strong>
        </div>
      </section>

      <TaskBoard :token="token" :username="username" :competitionId="compId" />
    </div>
  </div>
</template>

<style scoped>
.competition-detail {
  width: 100%;
  padding: 1rem 0;
}

.back-link {
  width: fit-content;
  color: var(--accent-cyan);
  text-decoration: none;
  font-family: var(--font-mono);
  font-weight: 800;
  opacity: 0.86;
}

.back-link::before {
  content: "< ";
  color: var(--accent-amber);
}

.back-link:hover {
  opacity: 1;
  text-shadow: 0 0 10px var(--accent-cyan-glow);
}

.error-state {
  color: var(--accent-danger);
  text-align: center;
}

.detail-body {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.operation-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 1rem;
  padding: 1.35rem;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background:
    linear-gradient(90deg, rgba(74, 200, 206, 0.09), transparent),
    var(--bg-card);
  box-shadow: 0 16px 45px rgba(0, 0, 0, 0.22);
}

.operation-header h2 {
  margin: 0;
  color: var(--text-main);
  font-family: var(--font-mono);
  font-size: clamp(1.5rem, 3vw, 2.2rem);
  line-height: 1.15;
}

.operation-code {
  min-width: 220px;
  padding: 0.9rem 1rem;
  border: 1px solid var(--border-subtle);
  border-left: 3px solid var(--accent-amber);
  border-radius: 6px;
  background: var(--bg-main);
  font-family: var(--font-mono);
}

.operation-code span {
  display: block;
  color: var(--text-muted);
  font-size: 0.78rem;
  margin-bottom: 0.3rem;
}

.operation-code strong {
  color: var(--accent-amber);
  letter-spacing: 0.08em;
}

@media (max-width: 760px) {
  .operation-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .operation-code {
    width: 100%;
    min-width: 0;
  }
}
</style>
