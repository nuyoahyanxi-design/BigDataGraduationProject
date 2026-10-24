<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElAlert, ElButton, ElCard, ElEmpty, ElOption, ElSelect, ElTag } from 'element-plus'
import { getRecommendations } from '@/api/recommendations'
import { algorithmNames, formatRecommendationScore, type RecommendationAlgorithm, type RecommendationsResponse } from '@/types/recommendations'
import ResourceCover from '@/components/ResourceCover.vue'
import { resourceError } from '@/services/resource-learning'
const router = useRouter()
const algorithm = ref<RecommendationAlgorithm>('content_v1')
const result = ref<RecommendationsResponse>()
const loading = ref(false), errorMessage = ref('')
let sequence = 0
async function load() {
  const current = ++sequence
  loading.value = true; errorMessage.value = ''; result.value = undefined
  try { const response = await getRecommendations(algorithm.value); if (current === sequence) result.value = response }
  catch (error) { if (current === sequence) errorMessage.value = resourceError(error) }
  finally { if (current === sequence) loading.value = false }
}
const interests = computed(() => Object.entries(result.value?.profile?.interest_weights ?? {}).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])))
const evidenceNames = { observed: '行为兴趣画像（可能包含显式兴趣）', explicit_only: '显式兴趣冷启动画像', no_evidence: '暂无兴趣证据' }
const eventNames = { resource_view: '浏览次数', learning_start: '开始学习次数', learning_complete: '完成学习次数', favorite_add: '收藏次数', favorite_remove: '取消收藏次数' }
function time(value: string | null | undefined) { return value ? new Date(value).toLocaleString('zh-CN', { timeZone: 'UTC', hour12: false }) + ' UTC' : '暂无' }
onMounted(load)
</script>
<template>
  <section class="recommendation-decor">
    <div class="page-heading"><h1><svg class="heading-spark" viewBox="0 0 32 32" aria-hidden="true"><path d="m16 3 3.7 9.3L29 16l-9.3 3.7L16 29l-3.7-9.3L3 16l9.3-3.7Z" fill="currentColor"/><circle cx="27" cy="5" r="2" fill="currentColor" opacity=".45"/></svg>个性化推荐</h1>
      <ElSelect v-model="algorithm" aria-label="推荐算法" :disabled="loading" @change="load">
        <ElOption v-for="(label, value) in algorithmNames" :key="value" :label="label" :value="value" />
      </ElSelect>
    </div>
    <details class="recommendation-method"><summary>推荐依据与得分说明</summary><p>内容推荐的综合推荐得分以百分比展示：兴趣标签匹配度占60%，个人学习行为占25%（浏览次数、开始学习次数、完成学习次数及收藏次数），资源热度占15%。章节浏览与视频播放按用户、章节、日期、类型去重后参与个人行为和热度，同课程每天贡献有上限；播放次数不代表观看时长。无历史行为时使用热门推荐回退。综合推荐得分不代表预测概率。热门推荐展示历史行为热度得分，与综合推荐得分不能直接比较；得分为0的补充资源请结合推荐理由查看。</p></details>
    <p v-if="loading" role="status">正在加载推荐与画像…</p>
    <template v-else-if="errorMessage">
      <ElAlert :title="errorMessage" type="error" :closable="false" role="alert" /><ElButton @click="load">重新加载</ElButton>
    </template>
    <template v-else-if="result">
      <section class="panel profile-summary">
        <h2>当前用户画像摘要</h2>
        <p>当前设置的兴趣：<ElTag v-for="tag in result.explicit_interest_tags" :key="tag" class="interest-tag">{{ tag }}</ElTag><span v-if="!result.explicit_interest_tags.length">暂未设置</span></p>
        <template v-if="result.profile">
          <p>{{ evidenceNames[result.profile.evidence] }}</p>
          <div class="resource-tags"><ElTag v-for="[tag, weight] in interests.slice(0,10)" :key="tag">{{ tag }} · {{ (weight * 100).toFixed(1) }}%</ElTag><span v-if="!interests.length">暂无画像兴趣权重</span></div>
          <details v-if="interests.length > 10"><summary>查看其余兴趣标签（{{ interests.length - 10 }} 项）</summary><div class="resource-tags"><ElTag v-for="[tag, weight] in interests.slice(10)" :key="tag">{{ tag }} · {{ (weight * 100).toFixed(1) }}%</ElTag></div></details>
          <dl class="user-details">
            <dt>活跃天数</dt><dd>{{ result.profile.active_days }}</dd>
            <dt>{{ result.profile.scope_label ? '正式课程行为次数' : '历史行为次数' }}</dt><dd><span v-for="(label, key) in eventNames" :key="key" class="metric-label">{{ label }} {{ result.profile.event_counts[key] }}</span></dd>
            <template v-if="result.profile.chapter_activity"><dt>章节与视频</dt><dd>章节浏览 {{ result.profile.chapter_activity.chapter_views }} 次 · 视频播放 {{ result.profile.chapter_activity.video_plays }} 次；浏览 {{ result.profile.chapter_activity.viewed_chapters }} 个章节，播放 {{ result.profile.chapter_activity.played_chapters }} 个章节，完成 {{ result.profile.chapter_activity.completed_chapters }} 个章节</dd></template>
            <dt>学习情况</dt><dd>已开始{{ result.profile.scope_label || '学习资源' }} {{ result.profile.started_resources }} 项，已完成{{ result.profile.scope_label || '学习资源' }} {{ result.profile.completed_resources }} 项；{{ result.profile.scope_label || '学习资源' }}完成率 {{ result.profile.completion_rate === null ? '暂无' : (result.profile.completion_rate * 100).toFixed(1) + '%' }}</dd>
            <dt>画像生成</dt><dd>{{ time(result.profile.generated_at) }}</dd>
            <dt>统计截止</dt><dd>{{ time(result.profile.as_of_utc) }}</dd>
            <dt>画像批次</dt><dd><details><summary>查看批次编号</summary>{{ result.profile.batch_id }}</details></dd>
          </dl>
          <p v-if="result.profile.scope_label">仅统计已发布、含章节的正式课程，排除验收、隐藏和下架资源；历史记录仍保留。</p>
          <p>画像按批次更新，最新操作可能尚未计入。完成率反映当前学习进度；历史完成操作次数不等于当前已完成资源数，不代表学习能力。</p>
        </template>
        <ElAlert v-else title="当前用户画像尚未生成，请先学习或设置兴趣，等待下一批处理。" type="info" :closable="false" />
      </section>
      <div class="batch-description">推荐生成：{{ time(result.generated_at) }}<details><summary>查看推荐批次</summary>{{ result.batch_id || '尚未发布' }}</details></div>
      <ElEmpty v-if="!result.items.length" :description="result.message || '暂无推荐结果，请先浏览学习资源'">
        <ElButton type="primary" @click="router.push({ name: 'resources' })">浏览学习资源</ElButton>
      </ElEmpty>
      <div v-else class="resource-grid">
        <ElCard v-for="item in result.items" :key="item.resource_id" class="resource-card resource-card--illustrated" shadow="never">
        <ResourceCover :resource-id="item.resource_id" />
          <ElTag type="info">原始排名 {{ item.rank }}</ElTag>
          <h2>{{ item.resource.title }}</h2><p class="resource-summary">{{ item.resource.summary }}</p>
          <div class="resource-tags"><ElTag v-for="tag in item.resource.tags" :key="tag">{{ tag }}</ElTag></div>
          <p class="recommendation-reason">{{ item.reason }}</p>
          <p>{{ algorithmNames[item.algorithm] }} · {{ formatRecommendationScore(item.score, item.algorithm) }}</p>
          <ElButton type="primary" @click="router.push({ name: 'resource-detail', params: { id: item.resource_id } })">查看资源</ElButton>
        </ElCard>
      </div>
    </template>
  </section>
</template>
