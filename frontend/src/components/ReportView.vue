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

function renderChart() {
  if (!chartEl.value || !props.chartConfig) return
  if (!chart) {
    chart = echarts.init(chartEl.value)
    window.addEventListener('resize', () => chart && chart.resize())
  }
  chart.setOption(props.chartConfig, true)
}

watch(() => props.chartConfig, renderChart, { deep: true })
onMounted(() => { if (props.chartConfig) renderChart() })
onBeforeUnmount(() => { if (chart) { chart.dispose(); chart = null } })
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
