<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import LoginRegister from './components/LoginRegister.vue'

const router = useRouter()
const route = useRoute()

const token = ref(localStorage.getItem('token') || '')
const username = ref(localStorage.getItem('username') || '')
const role = ref(localStorage.getItem('role') || '')
const isLight = ref(localStorage.getItem('theme') === 'light')

const updateThemeClass = () => {
  document.documentElement.classList.toggle('light-theme', isLight.value)
}

const toggleTheme = () => {
  isLight.value = !isLight.value
  localStorage.setItem('theme', isLight.value ? 'light' : 'dark')
  updateThemeClass()
}

onMounted(updateThemeClass)

const handleLogin = (data) => {
  token.value = data.token
  username.value = data.username
  role.value = data.role || 'member'
  localStorage.setItem('token', data.token)
  localStorage.setItem('username', data.username)
  localStorage.setItem('role', role.value)
}

const handleLogout = () => {
  token.value = ''
  username.value = ''
  role.value = ''
  localStorage.removeItem('token')
  localStorage.removeItem('username')
  localStorage.removeItem('role')
  router.push('/')
}
</script>

<template>
  <div>
    <header class="app-header">
      <div class="header-left">
        <h1 class="brand-logo text-neon-cyan" @click="router.push('/')">
          <span class="brand-icon">Y</span>
          <span>
            <span class="brand-name">YGGDRASIL_OS</span>
            <span class="brand-mode">WORLD TREE OPS</span>
          </span>
        </h1>

        <nav v-if="token" class="main-nav">
          <router-link to="/" class="nav-link" :class="{ active: route.path === '/' }">控制中心</router-link>
          <router-link to="/competitions" class="nav-link" :class="{ active: route.path.startsWith('/competitions') || route.path.startsWith('/tasks') }">比赛行动</router-link>
          <router-link to="/submit" class="nav-link" :class="{ active: route.path === '/submit' }">题目上传</router-link>
          <router-link v-if="role === 'admin'" to="/admin" class="nav-link" :class="{ active: route.path === '/admin' }">管理后台</router-link>
        </nav>
      </div>

      <div class="header-right">
        <button @click="toggleTheme" class="theme-toggle" :title="isLight ? '切换到暗色' : '切换到亮色'">
          <span class="theme-icon">{{ isLight ? 'OPS' : 'DAY' }}</span>
        </button>

        <div v-if="token" class="divider"></div>

        <span v-if="token" class="user-badge">
          <span class="user-label">OPERATOR::</span>
          <strong class="text-neon-purple user-name">{{ username }}</strong>
          <span class="role-chip">{{ role }}</span>
        </span>

        <button v-if="token" @click="handleLogout" class="btn-logout">
          退出
        </button>
      </div>
    </header>

    <main>
      <LoginRegister v-if="!token" @login-success="handleLogin" />
      <router-view v-else />
    </main>
  </div>
</template>

<style scoped>
.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1.5rem;
  position: sticky;
  top: 12px;
  z-index: 20;
  margin-bottom: 1.45rem;
  background: var(--bg-panel);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 0.78rem 1rem;
  box-shadow: 0 18px 55px rgba(0, 0, 0, 0.28);
  backdrop-filter: blur(12px);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 2.5rem;
  min-width: 0;
}

.brand-logo {
  margin: 0;
  font-size: 1.08rem;
  cursor: pointer;
  font-family: var(--font-mono);
  letter-spacing: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  white-space: nowrap;
  line-height: 1.05;
}

.brand-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: 1px solid rgba(74, 200, 206, 0.72);
  border-radius: 7px;
  background: rgba(74, 200, 206, 0.1);
  box-shadow: inset 0 0 18px rgba(74, 200, 206, 0.08);
  font-size: 0.98rem;
  font-weight: 900;
}

.brand-name {
  display: block;
  color: var(--text-main);
  font-weight: 900;
}

.brand-mode {
  display: block;
  margin-top: 2px;
  color: var(--accent-amber);
  font-size: 0.68rem;
  letter-spacing: 0.16em;
}

.main-nav {
  display: flex;
  gap: 0.45rem;
  border-left: 1px solid var(--border-subtle);
  padding-left: 1.4rem;
  flex-wrap: wrap;
}

.nav-link {
  color: var(--text-muted);
  text-decoration: none;
  font-weight: 600;
  position: relative;
  white-space: nowrap;
  border: 1px solid transparent;
  border-radius: 6px;
  padding: 0.48rem 0.72rem;
  font-family: var(--font-mono);
  font-size: 0.84rem;
  transition: color 0.18s ease, border-color 0.18s ease, background 0.18s ease;
}

.nav-link:hover,
.nav-link.active {
  color: var(--accent-cyan);
  border-color: rgba(74, 200, 206, 0.35);
  background: rgba(74, 200, 206, 0.09);
}

.nav-link.active::after {
  content: '';
  position: absolute;
  left: 10px;
  right: 10px;
  bottom: 4px;
  height: 1px;
  background: var(--accent-cyan);
  opacity: 0.8;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.theme-toggle {
  background: var(--bg-main);
  border: 1px solid var(--border-subtle);
  cursor: pointer;
  min-width: 50px;
  height: 38px;
  border-radius: 6px;
  padding: 0;
  font-family: var(--font-mono);
  font-weight: 800;
  color: var(--accent-amber);
}

.divider {
  height: 24px;
  width: 1px;
  background: var(--border-subtle);
}

.user-badge {
  font-size: 0.9em;
  color: var(--text-muted);
  font-family: var(--font-mono);
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-main);
  padding: 7px 12px;
  border-radius: 6px;
  border: 1px solid var(--border-subtle);
}

.role-chip {
  color: var(--accent-green);
  border-left: 1px solid var(--border-subtle);
  padding-left: 8px;
}

.btn-logout {
  padding: 6px 14px;
  font-size: 0.85em;
  background: rgba(255, 111, 97, 0.1);
  border-color: var(--accent-danger);
  color: var(--accent-danger);
  font-family: var(--font-mono);
  font-weight: bold;
  border-radius: 6px;
}

@media (max-width: 980px) {
  .app-header,
  .header-left {
    align-items: flex-start;
    flex-direction: column;
  }

  .main-nav {
    border-left: 0;
    padding-left: 0;
  }

  .header-right {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
