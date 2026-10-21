<script setup>
import { ref, watch, onMounted, onBeforeUnmount, computed } from 'vue'
import * as echarts from 'echarts'
import { marked } from 'marked'

const props = defineProps({
  report: { type: String, default: '' },
  streaming: { type: Boolean, default: false },
  chartConfig: { type: Object, default: null },
  emailResult: { type: String, default: '' },
})

const chartEl = ref(null)
let chart = null

const rendered = computed(() => {
  const md = marked.parse(props.report || '*等待生成...*')
  return props.streaming ? md + '<span class="cursor"></span>' : md
})

function onResize() {
  chart && chart.resize()
}

function renderChart() {
  if (!chartEl.value || !props.chartConfig) return
  // 每次重新生成时 chartConfig 会先置 null 再赋值，v-if 容器被销毁后重建为新的 DOM 节点。
  // 旧 ECharts 实例仍存在但绑定的是已脱离文档的旧节点，必须 dispose 后对新容器重新 init，
  // 否则第二次及以后的生成图表永远不会显示。
  if (!chart || chart.getDom() !== chartEl.value) {
    if (chart) chart.dispose()
    chart = echarts.init(chartEl.value)
    window.addEventListener('resize', onResize)
  }
  chart.setOption(props.chartConfig, true)
}

// flush: 'post' 确保 chartConfig 变化时，v-if 的图表容器已渲染完成后再初始化 ECharts，否则图表永远不会显示
watch(() => props.chartConfig, renderChart, { deep: true, flush: 'post' })
onMounted(() => { if (props.chartConfig) renderChart() })
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  if (chart) { chart.dispose(); chart = null }
})
</script>

<template>
  <div>
    <div class="report-body" v-html="rendered"></div>

    <template v-if="chartConfig">
      <div class="card-title" style="margin-top: 16px;">📈 数据趋势</div>
      <div ref="chartEl" id="chart"></div>
    </template>

    <div v-if="emailResult" class="email-result">{{ emailResult }}</div>
  </div>
</template>
