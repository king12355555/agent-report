<script setup>
defineProps({
  steps: { type: Array, default: () => [] },
  running: { type: Boolean, default: false },
})
</script>

<template>
  <div v-if="steps.length === 0" class="empty">
    点击「🚀 开始生成」，这里将实时展示 Agent 的每一步执行过程
  </div>
  <div v-else class="timeline">
    <div v-for="(step, i) in steps" :key="i" class="tl-item done">
      <div class="dot">✓</div>
      <div class="tl-title">{{ step.icon }} {{ step.title }}</div>
      <div class="tl-detail">{{ step.detail }}</div>
      <div v-if="step.data" class="tl-detail">
        <details>
          <summary style="cursor: pointer; color: var(--muted);">查看原始数据</summary>
          <pre>{{ step.data }}</pre>
        </details>
      </div>
    </div>
    <div v-if="running" class="tl-item running">
      <div class="dot">⋯</div>
      <div class="tl-title">执行中...</div>
    </div>
  </div>
</template>
