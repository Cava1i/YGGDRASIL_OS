<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const navigateTo = (path) => {
  router.push(path)
}
</script>

<template>
  <div class="home-container page-shell">
    <section class="command-hero">
      <div class="hero-copy">
        <p class="page-kicker">TACTICAL COLLABORATION ROOM</p>
        <h1 class="glitch-text" data-text="YGGDRASIL_OS">YGGDRASIL_OS</h1>
        <p class="subtitle">世界树式团队协作 · 题库调度 · 附件情报 · 管理审计</p>
      </div>
      <div class="ops-status">
        <span class="status-indicator"></span>
        <span>SYSTEM ONLINE</span>
        <strong>AWAITING COMMAND</strong>
      </div>
    </section>

    <div class="action-grid">
      <div class="cyber-card" @click="navigateTo('/competitions')">
        <div class="card-index">01</div>
        <h3 class="card-title">比赛行动</h3>
        <p class="card-desc">进入题目协作大表，查看答案一致率、WP、备注与附件线索。</p>
        <div class="card-footer">
          <span class="card-link">OPEN OPS</span>
        </div>
      </div>

      <div class="cyber-card" @click="navigateTo('/submit')">
        <div class="card-index">02</div>
        <h3 class="card-title">题目上传</h3>
        <p class="card-desc">手动录入单题，或导入 Excel 数据矩阵快速建立作战题库。</p>
        <div class="card-footer">
          <span class="card-link">LOAD DATA</span>
        </div>
      </div>

    </div>
  </div>
</template>

<style scoped>
.home-container {
  display: flex;
  flex-direction: column;
  padding: 1rem 0 2rem;
  min-height: calc(100vh - 140px);
}

.command-hero {
  position: relative;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  min-height: 310px;
  padding: clamp(2rem, 5vw, 4rem);
  overflow: hidden;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background:
    linear-gradient(90deg, rgba(74, 200, 206, 0.11), transparent 42%),
    repeating-linear-gradient(135deg, rgba(255, 255, 255, 0.025) 0, rgba(255, 255, 255, 0.025) 1px, transparent 1px, transparent 16px),
    var(--bg-panel);
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.28);
}

.command-hero::after {
  content: "";
  position: absolute;
  right: clamp(1rem, 5vw, 4rem);
  top: 2rem;
  width: min(420px, 42vw);
  aspect-ratio: 1;
  border: 1px solid rgba(74, 200, 206, 0.25);
  background:
    linear-gradient(90deg, transparent 49%, rgba(74, 200, 206, 0.22) 50%, transparent 51%),
    linear-gradient(0deg, transparent 49%, rgba(74, 200, 206, 0.22) 50%, transparent 51%),
    repeating-linear-gradient(0deg, transparent 0 22px, rgba(74, 200, 206, 0.08) 22px 23px),
    repeating-linear-gradient(90deg, transparent 0 22px, rgba(74, 200, 206, 0.08) 22px 23px);
  opacity: 0.46;
  transform: rotate(-3deg);
}

.hero-copy,
.ops-status {
  position: relative;
  z-index: 1;
}

.glitch-text {
  font-family: var(--font-mono);
  font-size: clamp(2.7rem, 7vw, 6.2rem);
  font-weight: 900;
  margin: 0;
  color: var(--text-main);
  letter-spacing: 0;
}

.subtitle {
  font-family: var(--font-mono);
  color: var(--text-soft);
  letter-spacing: 0;
  font-size: clamp(0.95rem, 1.7vw, 1.12rem);
  margin: 1rem 0 0;
  opacity: 0.85;
  font-weight: 600;
}

.ops-status {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--accent-green-bg);
  border: 1px solid rgba(123, 216, 137, 0.32);
  border-radius: 6px;
  font-family: var(--font-mono);
  font-size: 0.82rem;
  color: var(--accent-green);
  font-weight: 600;
  white-space: nowrap;
}

.ops-status strong {
  color: var(--text-main);
}

.status-indicator {
  width: 10px;
  height: 10px;
  background: var(--accent-green);
  border-radius: 50%;
  box-shadow: 0 0 10px var(--accent-green);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.4; }
  100% { opacity: 1; }
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(240px, 1fr));
  gap: 1rem;
}

.cyber-card {
  min-height: 220px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 1.5rem;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
  box-shadow: 0 14px 42px rgba(0, 0, 0, 0.18);
}

.cyber-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 3px;
  background: linear-gradient(90deg, var(--accent-cyan), var(--accent-amber));
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.cyber-card:hover {
  transform: translateY(-8px);
  background: var(--bg-card-hover);
  border-color: var(--accent-cyan);
  box-shadow: 0 20px 42px rgba(0, 0, 0, 0.34), 0 0 20px var(--accent-cyan-glow);
}

.cyber-card:hover::before {
  transform: scaleX(1);
}

.card-index {
  color: var(--accent-amber);
  font-family: var(--font-mono);
  font-size: 0.82rem;
  letter-spacing: 0.18em;
  margin-bottom: 1.5rem;
}

.card-title {
  font-family: var(--font-mono);
  color: var(--text-main);
  font-size: 1.45rem;
  margin: 0 0 1rem 0;
}

.card-desc {
  color: var(--text-muted);
  font-size: 0.98rem;
  line-height: 1.7;
  margin: 0 0 2rem;
}

.card-footer {
  border-top: 1px dashed var(--border-subtle);
  padding-top: 1.2rem;
}

.card-link {
  font-family: var(--font-mono);
  color: var(--accent-cyan);
  font-size: 0.9rem;
  font-weight: bold;
  opacity: 0.7;
  transition: all 0.3s;
  display: inline-block;
}

.cyber-card:hover .card-link {
  opacity: 1;
  transform: translateX(5px);
  text-shadow: 0 0 10px var(--accent-cyan-glow);
}

@media (max-width: 960px) {
  .command-hero {
    align-items: flex-start;
    flex-direction: column;
  }

  .action-grid {
    grid-template-columns: 1fr;
  }
}
</style>
