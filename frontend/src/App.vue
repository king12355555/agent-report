<script setup>
import { ref, reactive } from 'vue'
import AgentFlow from './components/AgentFlow.vue'
import ReportView from './components/ReportView.vue'

const reportType = ref('daily')
const running = ref(false)
const steps = reactive([])       // Agent 执行步骤
const reportTokens = ref('')     // 流式报告文本
const report = ref('')           // 最终报告
const chartConfig = ref(null)
const emailResult = ref('')
const error = ref('')
const status = ref('')

let es = null

function start() {
  // 重置状态
  steps.length = 0
  reportTokens.value = ''
  report.value = ''
  chartConfig.value = null
  emailResult.value = ''
  error.value = ''
  running.value = true
  status.value = 'Agent 启动中...'

  if (es) es.close()
  es = new EventSource(`/api/report/stream?type=${reportType.value}`)

  es.addEventListener('agent_step', (e) => {
    const step = JSON.parse(e.data)
    steps.push({ ...step, status: 'done' })
    status.value = step.title
  })

  es.addEventListener('agent_data', (e) => {
    const d = JSON.parse(e.data)
    // 附加到最近一个步骤，可展开查看原始数据
    if (steps.length) {
      steps[steps.length - 1].data = d.content
    }
  })

  es.addEventListener('report_token', (e) => {
    const d = JSON.parse(e.data)
    reportTokens.value += d.token
    status.value = 'LLM 撰写报告中...'
  })

  es.addEventListener('done', (e) => {
    const d = JSON.parse(e.data)
    report.value = d.report
    reportTokens.value = d.report
    if (d.chart_config) {
      try { chartConfig.value = JSON.parse(d.chart_config) } catch { chartConfig.value = null }
    }
    emailResult.value = d.email_result
    running.value = false
    status.value = '✅ 报告生成完成'
    es.close()
  })

  es.addEventListener('error', (e) => {
    error.value = 'Agent 执行出错，请查看后端日志'
    running.value = false
    status.value = '❌ 执行失败'
    es.close()
  })
}
</script>

<template>
  <header>
    <h1>🤖 AI Agent 自动化日报/周报生成器</h1>
    <p class="sub">LangGraph 多步工作流 · MCP 工具服务 · FastAPI SSE 实时流式输出 · Vue3 前端</p>
  </header>

  <div class="controls">
    <div class="btn-group">
      <button :class="{ active: reportType === 'daily' }" @click="reportType = 'daily'">📅 日报</button>
      <button :class="{ active: reportType === 'weekly' }" @click="reportType = 'weekly'">📆 周报</button>
    </div>
    <button class="btn-primary" :disabled="running" @click="start">
      {{ running ? '生成中...' : '🚀 开始生成' }}
    </button>
    <span class="status-bar">{{ status }}</span>
  </div>

  <div v-if="error" class="error-box">{{ error }}</div>

  <div class="main-grid">
    <div class="card">
      <div class="card-title">🧭 Agent 执行流</div>
      <AgentFlow :steps="steps" :running="running" />
    </div>
    <div class="card">
      <div class="card-title">📄 报告输出</div>
      <ReportView
        :report="reportTokens || report"
        :streaming="running"
        :chart-config="chartConfig"
        :email-result="emailResult"
      />
    </div>
  </div>
</template>
