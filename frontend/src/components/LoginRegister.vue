<script setup>
import { ref } from 'vue'
import { api } from '../api'

const emit = defineEmits(['login-success'])

const isLogin = ref(true)
const form = ref({
  username: '',
  password: '',
  inviteCode: ''
})
const message = ref('')
const isError = ref(false)

const handleSubmit = async () => {
  message.value = '请求中...'
  isError.value = false

  try {
    if (isLogin.value) {
      const res = await api.post('/api/login', {
        username: form.value.username,
        password: form.value.password
      })
      message.value = '登录成功'
      emit('login-success', res.data)
      return
    }

    await api.post('/api/register', {
      username: form.value.username,
      password: form.value.password,
      inviteCode: form.value.inviteCode
    })
    message.value = '注册成功，请登录'
    form.value.password = ''
    isLogin.value = true
  } catch (error) {
    isError.value = true
    message.value = error.response?.data?.error || '操作失败'
  }
}
</script>

<template>
  <div class="auth-shell">
    <div class="auth-brief">
      <p class="page-kicker">SECURE ACCESS</p>
      <h1>YGGDRASIL_OS</h1>
      <p>世界树式团队协作战情室</p>
      <div class="brief-grid">
        <span>OPS</span>
        <strong>ONLINE</strong>
        <span>AUTH</span>
        <strong>REQUIRED</strong>
      </div>
    </div>

    <div class="auth-panel">
      <h2>{{ isLogin ? '系统登录' : '注册账号' }}</h2>

      <form @submit.prevent="handleSubmit" class="auth-form">
        <label>
          <span>用户名</span>
          <input v-model="form.username" type="text" required autocomplete="username" />
        </label>

        <label>
          <span>密码</span>
          <input v-model="form.password" type="password" required autocomplete="current-password" />
        </label>

        <label v-if="!isLogin">
          <span>邀请码</span>
          <input v-model="form.inviteCode" type="text" required autocomplete="off" />
        </label>

        <button type="submit">
          {{ isLogin ? '登录' : '注册' }}
        </button>
      </form>

      <div class="auth-switch">
        <a href="#" @click.prevent="isLogin = !isLogin">
          {{ isLogin ? '没有账号？点击注册' : '返回登录' }}
        </a>
      </div>

      <p v-if="message" class="auth-message" :class="{ error: isError }">
        {{ message }}
      </p>
    </div>
  </div>
</template>

<style scoped>
.auth-shell {
  display: grid;
  grid-template-columns: minmax(280px, 0.9fr) minmax(320px, 450px);
  gap: 1rem;
  align-items: stretch;
  max-width: 980px;
  margin: clamp(2rem, 8vh, 5rem) auto;
}

.auth-brief {
  position: relative;
  container-type: inline-size;
  min-height: 470px;
  padding: 2rem;
  overflow: hidden;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgba(74, 200, 206, 0.13), transparent 48%),
    repeating-linear-gradient(90deg, rgba(255, 255, 255, 0.03) 0 1px, transparent 1px 18px),
    var(--bg-panel);
  box-shadow: 0 22px 70px rgba(0, 0, 0, 0.26);
}

.auth-brief::after {
  content: "";
  position: absolute;
  inset: 28px;
  border: 1px solid rgba(74, 200, 206, 0.18);
  pointer-events: none;
}

.auth-brief h1 {
  position: relative;
  z-index: 1;
  max-width: 100%;
  margin: 0;
  color: var(--text-main);
  font-family: var(--font-mono);
  font-size: clamp(1.75rem, 7.2cqw, 3.25rem);
  line-height: 1.05;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.auth-brief p:not(.page-kicker) {
  position: relative;
  z-index: 1;
  margin: 1rem 0 0;
  color: var(--text-soft);
  font-family: var(--font-mono);
}

.brief-grid {
  position: absolute;
  left: 2rem;
  right: 2rem;
  bottom: 2rem;
  z-index: 1;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.8rem 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-subtle);
  font-family: var(--font-mono);
}

.brief-grid span {
  color: var(--text-muted);
}

.brief-grid strong {
  color: var(--accent-amber);
}

.auth-panel {
  padding: 2rem;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  box-shadow: 0 22px 70px rgba(0, 0, 0, 0.26);
}

.auth-panel h2 {
  margin: 0;
  text-align: center;
  font-family: var(--font-mono);
  color: var(--accent-cyan);
  font-size: 1.7rem;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  margin-top: 2.5rem;
}

.auth-form label {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.auth-form span {
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 0.9rem;
  font-weight: 600;
}

.auth-form button {
  width: 100%;
  padding: 1rem;
  margin-top: 0.5rem;
  font-family: var(--font-mono);
  letter-spacing: 0.08em;
  background: rgba(74, 200, 206, 0.12);
  border-color: var(--accent-cyan);
  color: var(--accent-cyan);
  font-weight: 800;
}

.auth-switch {
  margin-top: 2rem;
  text-align: center;
}

.auth-switch a {
  color: var(--accent-purple);
  text-decoration: none;
  font-family: var(--font-mono);
  font-size: 0.95rem;
  font-weight: 600;
}

.auth-message {
  margin-top: 1.5rem;
  color: var(--accent-green);
  text-align: center;
  font-family: var(--font-mono);
  font-size: 0.95rem;
  font-weight: 600;
  background: rgba(123, 216, 137, 0.1);
  padding: 0.8rem;
  border-radius: 6px;
  border: 1px solid rgba(123, 216, 137, 0.3);
}

.auth-message.error {
  color: var(--accent-danger);
  background: rgba(255, 111, 97, 0.1);
  border-color: rgba(255, 111, 97, 0.3);
}

@media (max-width: 820px) {
  .auth-shell {
    grid-template-columns: 1fr;
    margin: 1rem auto;
  }

  .auth-brief {
    min-height: 280px;
    padding: 1.5rem;
  }
}
</style>
