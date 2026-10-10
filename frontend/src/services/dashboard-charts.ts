import type { EChartsOption } from 'echarts'
import type { DashboardResponse } from '@/types/dashboard'
import { categories } from '@/types/resources'
import { algorithmNames } from '@/types/recommendations'

export function dashboardCharts(result: DashboardResponse) {
  const metric = result.data?.metrics
  const tooltip = { trigger: 'item' as const, renderMode: 'richText' as const }
  const trend: EChartsOption = {
    tooltip: { trigger: 'axis', renderMode: 'richText' }, legend: { bottom: 0 },
    grid: { left: 45, right: 20, bottom: 80, top: 20 },
    xAxis: { type: 'category', data: metric?.behavior.daily.map((row) => row.day) ?? [], axisLabel: { rotate: 35 } },
    yAxis: { type: 'value', minInterval: 1 },
    series: ([['resource_view','浏览次数'],['learning_start','开始学习次数'],['learning_complete','完成学习次数'],['favorite_add','收藏次数'],['favorite_remove','取消收藏次数']] as const)
      .map(([key, name]) => ({ type: 'line', name, data: metric?.behavior.daily.map((row) => row[key]) ?? [], smooth: false })),
  }
  const distribution: EChartsOption = { tooltip, legend: { bottom: 0 }, series: [{ type: 'pie', radius: ['35%','65%'], center: ['50%','43%'],
    data: metric?.resource_categories.map((row) => ({ name: categories.find(([code]) => code === row.category)?.[1] ?? row.category, value: row.count })) ?? [] }] }
  const completion: EChartsOption = { tooltip, legend: { bottom: 0 }, series: [{ type: 'pie', radius: ['35%','65%'], center: ['50%','43%'],
    data: [{ name: '学习中', value: metric?.learning.in_progress ?? 0 }, { name: '已完成', value: metric?.learning.completed ?? 0 }] }] }
  const recommendation: EChartsOption = { tooltip: { trigger: 'axis', renderMode: 'richText' }, grid: { left: 45, right: 20, bottom: 50, top: 20 },
    xAxis: { type: 'category', data: result.recommendations?.algorithms.map((row) => algorithmNames[row.algorithm as keyof typeof algorithmNames] ?? row.algorithm) ?? [] },
    yAxis: { type: 'value', minInterval: 1 }, series: [{ type: 'bar', name: '发布推荐条数', data: result.recommendations?.algorithms.map((row) => row.rows) ?? [], barMaxWidth: 60 }] }
  return { trend, distribution, completion, recommendation }
}
