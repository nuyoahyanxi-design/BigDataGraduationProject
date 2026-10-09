<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { init, use, type ECharts } from 'echarts/core'
import { LineChart, PieChart, BarChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsOption } from 'echarts'
use([LineChart, PieChart, BarChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])
const props = defineProps<{ option: EChartsOption; label: string }>()
const element = ref<HTMLDivElement>()
let chart: ECharts | undefined
let observer: ResizeObserver | undefined
onMounted(() => {
  if (!element.value) return
  chart = init(element.value)
  chart.setOption(props.option, { notMerge: true })
  observer = new ResizeObserver(() => chart?.resize())
  observer.observe(element.value)
})
watch(() => props.option, (option) => chart?.setOption(option, { notMerge: true }), { deep: true })
onBeforeUnmount(() => { observer?.disconnect(); chart?.dispose(); chart = undefined })
</script>
<template><div ref="element" class="dashboard-chart" role="img" :aria-label="label" /></template>
