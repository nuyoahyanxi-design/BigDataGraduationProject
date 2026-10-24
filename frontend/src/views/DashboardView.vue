<script setup lang="ts">
import PublicEducationDashboard from '@/components/PublicEducationDashboard.vue'
import { computed, onMounted, ref } from 'vue'
import { ElAlert, ElButton, ElCard, ElEmpty } from 'element-plus'
import EChart from '@/components/EChart.vue'
import { getDashboard } from '@/api/dashboard'
import { dashboardCharts } from '@/services/dashboard-charts'
import { resourceError } from '@/services/resource-learning'
import type { DashboardResponse } from '@/types/dashboard'
const source = ref<'platform'|'oulad'>('platform')
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
const dataNotes = ref<HTMLDetailsElement>()
function openDataNotes() {
  if (!dataNotes.value) return
  dataNotes.value.open = true
  dataNotes.value.scrollIntoView({ block: 'start', behavior: 'auto' })
  dataNotes.value.querySelector('summary')?.focus()
}
onMounted(load)
</script>
<template>
  <section class="dashboard-decor">
    <div class="dashboard-source-switch" role="group" aria-label="看板数据来源"><button type="button" :aria-pressed="source==='platform'" @click="source='platform'">平台数据</button><button type="button" :aria-pressed="source==='oulad'" @click="source='oulad'">OULAD公开教育数据</button></div>
    <PublicEducationDashboard v-if="source==='oulad'" />
    <template v-else>
    <header class="dashboard-overview">
      <div class="overview-topline"><span class="overview-eyebrow">LEARNING ANALYTICS</span><ElButton :loading="loading" @click="load">刷新展示</ElButton></div>
      <h1>数据分析看板</h1><p class="overview-description">平台学习与资源概览</p>
      <div class="overview-foot"><div class="overview-badges"><span>管理员只读</span><span>离线学习统计</span><span>演示样本</span></div><span v-if="data" class="overview-time">更新于 {{ time(data.generated_at) }}</span><button v-if="data && response?.available" type="button" class="overview-notes" @click="openDataNotes">查看数据说明 <span aria-hidden="true">↗</span></button></div>
      <svg class="overview-art" viewBox="0 0 220 100" fill="none" aria-hidden="true"><path d="M16 73 66 43l52 19 72-45M66 43l22-27m30 46 56 26" stroke="currentColor" stroke-width="1.3"/><circle cx="16" cy="73" r="5"/><circle cx="66" cy="43" r="8"/><circle cx="118" cy="62" r="6"/><circle cx="190" cy="17" r="5"/><circle cx="88" cy="16" r="4"/><circle cx="174" cy="88" r="4"/></svg>
    </header>
    <p class="dashboard-context-note">{{ data?.metrics.learning.scope_label ? '正式课程统计按同一批次更新，排除验收、隐藏及下架资源。' : '学习统计按批次更新，资源统计读取当前数据。' }}</p>
    <p v-if="loading" role="status">正在读取已发布统计…</p>
    <ElAlert v-else-if="error" :title="error" type="error" :closable="false" role="alert" />
    <ElEmpty v-else-if="!response?.available || !data" :description="response?.message || '尚无可展示的统计数据'" />
    <template v-else>
      <div class="dashboard-counters">
        <ElCard shadow="never" class="metric-decor metric-decor--1"><span class="metric-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="8" r="3"/><path d="M5 21v-2a7 7 0 0 1 14 0v2M3 10v5m18-5v5"/></svg></span><span>统计用户总数</span><strong>{{ data.metrics.users.total }}</strong><small>活跃学习者 {{ data.metrics.users.active_learners }}，管理员 {{ data.metrics.users.admins }}</small></ElCard>
        <ElCard shadow="never" class="metric-decor metric-decor--2"><span class="metric-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 5q4-2 8 0 4-2 8 0v15q-4-2-8 0-4-2-8 0ZM12 5v15"/></svg></span><span>{{ data.metrics.resources.scope_label ? '正式课程总数' : '学习资源总数' }}</span><strong>{{ data.metrics.resources.total }}</strong><small>已发布 {{ data.metrics.resources.published }} · {{ data.metrics.resources.scope_label ? '批次内正式课程目录' : '当前资源目录' }}</small></ElCard>
        <ElCard shadow="never" class="metric-decor metric-decor--3"><span class="metric-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="m3 15 5-5 5 3 8-9M16 4h5v5M3 21h18"/></svg></span><span>{{ data.metrics.learning.scope_label ? '正式课程有效学习行为' : '累计有效学习行为' }}</span><strong>{{ data.metrics.behavior.total_effective_events }}</strong><small>已清洗的学习者行为记录</small></ElCard>
        <ElCard shadow="never" class="metric-decor metric-decor--4"><span class="metric-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="8"/><path d="M8 17v-2a4 4 0 0 1 8 0v2"/><circle cx="12" cy="9" r="2"/></svg></span><span>配套画像用户数</span><strong>{{ response?.profiles?.users ?? 0 }}</strong><small>当前统计批次的学习者画像</small></ElCard>
      </div>
      <div class="dashboard-panels">
        <ElCard shadow="never"><h2>用户行为趋势</h2><p class="chart-source">统计截止日前 30 天 · {{ data.metrics.behavior.timezone }}</p>
          <EChart v-if="data.metrics.behavior.window_events > 0" :option="charts.trend" label="用户行为趋势图" /><ElEmpty v-else description="该统计窗口暂无有效行为" /></ElCard>
        <ElCard shadow="never"><h2>资源分类分布</h2><p class="chart-source">纳入统计的已发布资源分类</p>
          <EChart v-if="data.metrics.resource_categories.length" :option="charts.distribution" label="资源分类分布图" /><ElEmpty v-else description="暂无已发布资源" /></ElCard>
        <ElCard shadow="never"><h2>学习完成情况</h2><p class="chart-source">活跃学习者已开始的资源学习记录</p>
          <p>已开始{{ data.metrics.learning.scope_label || '学习资源' }} {{ data.metrics.learning.started_pairs }} 项 · {{ data.metrics.learning.scope_label || '学习资源' }}完成率 {{ percent(data.metrics.learning.completion_rate) }}</p>
          <EChart v-if="data.metrics.learning.started_pairs > 0" :option="charts.completion" label="学习完成情况图" /><ElEmpty v-else description="暂无已开始的学习记录" /></ElCard>
        <ElCard shadow="never"><h2>推荐结果统计</h2><p class="chart-source">当前批次生成的推荐条数，非页面浏览量</p>
          <EChart v-if="response?.recommendations && response.recommendations.rows > 0" :option="charts.recommendation" label="推荐结果统计图" /><ElEmpty v-else description="配套批次暂无推荐结果" /></ElCard>
      </div>
      <section v-if="data.metrics.chapter" class="panel chapter-analytics"><h2>章节与视频学习</h2><p>独立章节事件统计 · 播放次数不代表观看时长</p><div class="dashboard-counters"><div><span>章节浏览</span><strong>{{ data.metrics.chapter.chapter_views }}</strong><small>{{ data.metrics.chapter.viewed_pairs }} 个用户与章节组合</small></div><div><span>视频播放</span><strong>{{ data.metrics.chapter.video_plays }}</strong><small>{{ data.metrics.chapter.play_users }} 位学习者 · {{ data.metrics.chapter.played_pairs }} 个用户与章节组合</small></div><div><span>已完成章节</span><strong>{{ data.metrics.chapter.completed_pairs }}</strong><small>按用户与章节去重，不等于课程完成数</small></div></div><EChart :option="{ tooltip: { trigger: 'axis' }, legend: { data: ['章节浏览','视频播放'] }, xAxis: { type: 'category', data: data.metrics.chapter.daily.map(r=>r.day) }, yAxis: { type: 'value', minInterval: 1 }, series: [{ name:'章节浏览',type:'line',data:data.metrics.chapter.daily.map(r=>r.chapter_view),color:'#a9583e' },{ name:'视频播放',type:'line',data:data.metrics.chapter.daily.map(r=>r.video_play),color:'#648883' }] }" label="章节与视频行为趋势图" /></section>
      <details ref="dataNotes" class="dashboard-data-notes">
        <summary>数据来源与批次详情<span>统计口径、清洗记录与 Spark 配套结果</span></summary>
      <section class="panel batch-panel">
        <h2>数据与批次</h2><p>{{ data.metrics.learning.scope_label ? '正式课程范围：已发布、含章节，且非验收及隐藏资源；课程总数和学习统计均来自同一快照。' : '完整来源与样本性质见下方记录。' }}</p>
        <dl class="user-details"><dt>数据更新</dt><dd>{{ time(data.generated_at) }}</dd><dt>统计截止</dt><dd>{{ time(data.as_of_utc) }}</dd>
          <dt>看板批次</dt><dd>{{ data.batch_id }}</dd><dt>源批次</dt><dd>{{ data.source_batch_id }}</dd><dt>Spark</dt><dd>{{ data.spark_version }}</dd>
          <dt>来源</dt><dd>{{ data.source }}</dd><dt>样本性质</dt><dd>{{ data.dataset_origin }}</dd></dl>
        <p>清洗输入 {{ data.quality.input_count }} 条，过滤 {{ data.quality.filtered_count }} 条，输出 {{ data.quality.output_count }} 条。</p>
      </section>
      <section class="panel batch-panel"><h2>画像与推荐统计</h2><dl class="user-details">
        <dt>画像批次</dt><dd>{{ response?.profiles?.batch_id || '未生成' }}</dd>
        <dt>推荐批次</dt><dd>{{ response?.recommendations?.batch_id || '未生成' }}</dd><dt>推荐生成</dt><dd>{{ time(response?.recommendations?.generated_at) }}</dd></dl>
        <p v-for="row in response?.recommendations?.algorithms ?? []" :key="row.algorithm">{{ row.algorithm }}：{{ row.rows }} 条，{{ row.users }} 位用户，{{ row.resources }} 个不同资源。</p>
        <p>完成率反映已记录的学习进度，不用于评价学习能力。本页使用开发验收样本，结果用于功能验证，不能作为真实学生使用效果的证据。</p>
      </section>
      </details>
    </template>
    </template>
  </section>
</template>

<style scoped>
.chapter-analytics{margin-top:24px}.chapter-analytics .dashboard-counters{grid-template-columns:repeat(3,minmax(0,1fr))}.chapter-analytics .dashboard-counters>div{padding:18px;border:1px solid #e6dfd8;border-radius:8px;background:#faf9f5}@media(max-width:600px){.chapter-analytics .dashboard-counters{grid-template-columns:1fr}}

.dashboard-source-switch{display:flex;gap:4px;flex-wrap:wrap;margin-bottom:18px;padding:4px;width:fit-content;max-width:100%;background:#f0ece4;border:1px solid #e6dfd8;border-radius:9px}.dashboard-source-switch button{border:0;background:transparent;padding:9px 15px;font:inherit;font-size:12px;color:#77736b;border-radius:6px;cursor:pointer}.dashboard-source-switch button[aria-pressed="true"]{background:#fff;color:#a9583e;box-shadow:0 1px 4px #55412c0c}.dashboard-source-switch button:focus-visible{outline:2px solid #a9583e;outline-offset:2px}

.dashboard-overview{position:relative;isolation:isolate;overflow:hidden;background:linear-gradient(110deg,#f0f3ef,#f5f1e9);border:1px solid #dfe5dd;border-radius:14px;padding:22px 26px}.overview-topline{display:flex;align-items:center;justify-content:space-between;gap:12px;position:relative;z-index:1}.overview-eyebrow{font-size:10px;letter-spacing:2px;font-weight:600;color:#738377}.dashboard-overview h1{font-size:28px;letter-spacing:-.025em;color:#292f29;line-height:1.4;margin:5px 0 6px;position:relative;z-index:1}.overview-description{font-size:13px;margin:0 0 18px;color:#7a8176}.overview-foot{display:flex;align-items:center;gap:14px;flex-wrap:wrap;position:relative;z-index:1}.overview-badges{display:flex;gap:7px;flex-wrap:wrap}.overview-badges>span{font-size:10px;padding:4px 8px;border:1px solid #d9e0d5;background:#ffffff80;border-radius:5px;color:#6c7968}.overview-time{font-size:11px;color:#7b8174}.overview-notes{border:0;background:transparent;color:#8e624b;font:inherit;font-size:11px;cursor:pointer;padding:5px 0;margin-left:auto}.overview-notes:focus-visible{outline:2px solid #a9583e;outline-offset:3px}.overview-art{position:absolute;right:100px;top:18px;width:220px;height:100px;color:#8fa18b;opacity:.22;stroke:currentColor;pointer-events:none}.overview-art circle{fill:#f5f3ea;stroke-width:1.5}.dashboard-context-note{font-size:11px;margin:12px 2px 0;line-height:1.8;color:#89877c}.dashboard-decor .dashboard-counters{margin:20px 0 24px}.dashboard-decor .metric-decor .el-card__body{padding:20px}.dashboard-decor .metric-icon{float:right;margin:0 0 10px 8px;width:30px;height:30px}.dashboard-decor .dashboard-counters strong{font-size:34px;margin:10px 0 8px}.dashboard-decor .dashboard-counters small{font-size:10px;line-height:1.7;clear:both}.dashboard-data-notes{border:1px solid #e6dfd8;background:#fff;border-radius:10px;margin-top:24px;scroll-margin-top:24px}.dashboard-data-notes>summary{display:flex;justify-content:space-between;align-items:center;gap:14px;padding:20px 24px;cursor:pointer;font-size:14px;font-weight:600;color:#565b50;list-style:none}.dashboard-data-notes>summary::after{content:'＋';font-size:17px;font-weight:400;color:#8d8b7b}.dashboard-data-notes[open]>summary::after{content:'−'}.dashboard-data-notes>summary span{font-size:11px;font-weight:400;color:#8c8b7f;margin-left:auto}.dashboard-data-notes>summary:focus-visible{outline:2px solid #a9583e;outline-offset:3px}.dashboard-data-notes .batch-panel{border:0;border-top:1px solid #ece6df;border-radius:0;margin:0;background:transparent}.dashboard-data-notes .batch-panel:last-child{border-radius:0 0 10px 10px}
@media(max-width:600px){.dashboard-overview{padding:20px}.dashboard-overview h1{font-size:25px}.overview-art{right:-45px;top:42px;width:180px;opacity:.12}.overview-foot{gap:10px}.overview-notes{margin-left:0}.overview-time{width:100%}.dashboard-data-notes>summary{padding:18px}.dashboard-data-notes>summary span{display:none}.dashboard-decor .metric-decor .el-card__body{padding:18px}}
</style>
