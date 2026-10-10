<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElAlert, ElButton, ElCard, ElEmpty } from 'element-plus'
import EChart from '@/components/EChart.vue'
import { getDashboard } from '@/api/dashboard'
import { dashboardCharts } from '@/services/dashboard-charts'
import { resourceError } from '@/services/resource-learning'
import type { DashboardResponse } from '@/types/dashboard'
const response = ref<DashboardResponse>(), loading = ref(false), error = ref('')
async function load() {
  if (loading.value) return
  loading.value = true; error.value = ''; response.value = undefined
  try { response.value = await getDashboard() } catch (reason) { error.value = resourceError(reason) }
  finally { loading.value = false }
}
const charts = computed(() => dashboardCharts(response.value ?? { available: false, data: null, profiles: null, recommendations: null, message: null }))
const data = computed(() => response.value?.data)
function time(value: string | undefined | null) {
  if (!value) return '尚未生成'
  const iso = value.replace(' ', 'T')
  const utc = /(?:Z|[+-]\d{2}:\d{2})$/i.test(iso) ? iso : iso + 'Z'
  return new Date(utc).toLocaleString('zh-CN', { timeZone: 'UTC', hour12: false }) + ' UTC'
}
function percent(value: number | null) { return value === null ? '暂无' : new Intl.NumberFormat('zh-CN',{ style:'percent', maximumFractionDigits:1 }).format(value) }
onMounted(load)
</script>
<template>
  <section>
    <div class="page-heading"><h1>数据分析看板</h1><ElButton :loading="loading" @click="load">刷新展示</ElButton></div>
    <p>管理员只读统计 · 展示已冻结批次；刷新页面不会触发Spark重算。</p>
    <p v-if="loading" role="status">正在读取已发布统计…</p>
    <ElAlert v-else-if="error" :title="error" type="error" :closable="false" role="alert" />
    <ElEmpty v-else-if="!response?.available || !data" :description="response?.message || '尚无可展示的统计数据'" />
    <template v-else>
      <section class="panel batch-panel">
        <h2>数据与批次</h2>
        <dl class="user-details"><dt>数据更新</dt><dd>{{ time(data.generated_at) }}</dd><dt>统计截止</dt><dd>{{ time(data.as_of_utc) }}</dd>
          <dt>看板批次</dt><dd>{{ data.batch_id }}</dd><dt>源批次</dt><dd>{{ data.source_batch_id }}</dd><dt>Spark</dt><dd>{{ data.spark_version }}</dd>
          <dt>来源</dt><dd>{{ data.source }}</dd><dt>样本性质</dt><dd>{{ data.dataset_origin }}</dd></dl>
        <p>清洗输入 {{ data.quality.input_count }} 条，过滤 {{ data.quality.filtered_count }} 条，输出 {{ data.quality.output_count }} 条。</p>
      </section>
      <div class="dashboard-counters">
        <ElCard shadow="never"><span>快照用户总数</span><strong>{{ data.metrics.users.total }}</strong><small>活跃学习者 {{ data.metrics.users.active_learners }}，管理员 {{ data.metrics.users.admins }} · ODS.users</small></ElCard>
        <ElCard shadow="never"><span>当前教学资源总数</span><strong>{{ data.metrics.resources.total }}</strong><small>已发布 {{ data.metrics.resources.published }} · 实时MySQL（排除联调资源）</small></ElCard>
        <ElCard shadow="never"><span>有效学习者行为（全快照）</span><strong>{{ data.metrics.behavior.total_effective_events }}</strong><small>DWD.learning_events</small></ElCard>
        <ElCard shadow="never"><span>配套画像用户数</span><strong>{{ response?.profiles?.users ?? 0 }}</strong><small>user_profiles · {{ response?.profiles?.batch_id || '未生成' }}</small></ElCard>
      </div>
      <div class="dashboard-panels">
        <ElCard shadow="never"><h2>用户行为趋势</h2><p class="chart-source">Spark daily_metrics · 截止自然日前30天 · {{ data.metrics.behavior.timezone }}</p>
          <EChart v-if="data.metrics.behavior.window_events > 0" :option="charts.trend" label="用户行为趋势图" /><ElEmpty v-else description="该统计窗口暂无有效行为" /></ElCard>
        <ElCard shadow="never"><h2>资源分类分布</h2><p class="chart-source">实时MySQL · 当前已发布资源（排除联调资源）</p>
          <EChart v-if="data.metrics.resource_categories.length" :option="charts.distribution" label="资源分类分布图" /><ElEmpty v-else description="暂无已发布资源" /></ElCard>
        <ElCard shadow="never"><h2>学习完成情况</h2><p class="chart-source">ODS.learning_progress · 活跃学习者已开始的进度记录</p>
          <p>已开始学习资源 {{ data.metrics.learning.started_pairs }} 项 · 课程完成率 {{ percent(data.metrics.learning.completion_rate) }}</p>
          <EChart v-if="data.metrics.learning.started_pairs > 0" :option="charts.completion" label="学习完成情况图" /><ElEmpty v-else description="暂无已开始的学习记录" /></ElCard>
        <ElCard shadow="never"><h2>推荐结果统计</h2><p class="chart-source">recommendation_results · 配套离线批次发布行，非在线展示量或实验Coverage</p>
          <EChart v-if="response?.recommendations && response.recommendations.rows > 0" :option="charts.recommendation" label="推荐结果统计图" /><ElEmpty v-else description="配套批次暂无推荐结果" /></ElCard>
      </div>
      <section class="panel batch-panel"><h2>Spark配套结果</h2><dl class="user-details">
        <dt>画像批次</dt><dd>{{ response?.profiles?.batch_id || '未生成' }}</dd>
        <dt>推荐批次</dt><dd>{{ response?.recommendations?.batch_id || '未生成' }}</dd><dt>推荐生成</dt><dd>{{ time(response?.recommendations?.generated_at) }}</dd></dl>
        <p v-for="row in response?.recommendations?.algorithms ?? []" :key="row.algorithm">{{ row.algorithm }}：{{ row.rows }} 条，{{ row.users }} 位用户，{{ row.resources }} 个不同资源。</p>
        <p>课程完成率只描述已记录的资源学习流程，不代表学习能力；开发验收样本不能证明真实使用效果。</p>
      </section>
    </template>
  </section>
</template>
