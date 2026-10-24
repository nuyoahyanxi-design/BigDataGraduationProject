<script setup lang="ts">
import ResourceCover from '@/components/ResourceCover.vue'
import { computed, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElAlert, ElButton, ElTag } from 'element-plus'
import { ResourceLearning } from '@/services/resource-learning'
import { getCourse } from '@/api/courses'
import { chapterPercent, chapterStatus, courseButton, type Course } from '@/types/courses'
import { categories, typeNames, difficultyNames, progressNames, safeContentUrl } from '@/types/resources'
const route = useRoute(), router = useRouter()
const controller = shallowRef<ResourceLearning>()
const course = shallowRef<Course>()
const courseError = shallowRef('')
const courseReady = shallowRef(false)
const progress = computed(() => course.value?.chapters.length ? chapterStatus(course.value.chapters) : state.value?.progress ?? 'not_started')
const percent = computed(() => chapterPercent(course.value?.chapters ?? []))
const invalidId = shallowRef(false)
const state = computed(() => controller.value?.state)
const resource = computed(() => state.value?.resource)
const contentUrl = computed(() => safeContentUrl(resource.value?.content_url ?? null))
const categoryLabel = computed(() => categories.find(([code]) => code === resource.value?.category_code)?.[1] ?? resource.value?.category_code)
function formatTime(value: string | null | undefined) { return value ? value.replace('T', ' ') + (/[zZ]|[+-]\d\d:\d\d$/.test(value) ? '' : ' UTC') : '暂无' }
async function load() {
  const id = Number(route.params.id)
  invalidId.value = !/^[1-9]\d*$/.test(String(route.params.id)) || !Number.isSafeInteger(id)
  controller.value = undefined; course.value=undefined; courseReady.value=false; courseError.value=''
  if (invalidId.value) return
  const next = new ResourceLearning(id); controller.value = next
  await next.load()
  if(controller.value===next && next.state.resource) {
    try { const result=await getCourse(id); if(controller.value===next){course.value=result;courseReady.value=true} }
    catch { if(controller.value===next)courseError.value='课程状态暂时无法读取，请重新加载详情' }
  }
  if (controller.value === next && next.state.resource?.status === 'published') await next.recordView()
}
async function refreshState() { try { await controller.value?.refreshState() } catch { /* stateError is displayed */ } }
watch(() => route.params.id, load, { immediate: true })
</script>
<template>
  <section class="resource-detail-page">
    <ElButton @click="router.push({ name: 'resources' })">返回资源列表</ElButton>
    <ElAlert v-if="invalidId" title="资源编号无效" type="error" :closable="false" />
    <p v-else-if="state?.loading" role="status">正在加载详情…</p>
    <template v-else-if="state">
      <ElAlert v-if="state.error" :title="state.error" type="error" :closable="false" role="alert" />
      <ElButton v-if="state.error" @click="load">重新加载</ElButton>
      <article v-if="resource" class="panel resource-detail">
        <header class="detail-hero">
          <div class="detail-cover"><ResourceCover :resource-id="resource.id" /></div>
          <div class="detail-intro"><p class="detail-eyebrow">探索 · 理解 · 实践</p>
        <h1>{{ resource.title }}</h1><p>{{ resource.summary }}</p>
        <div class="resource-meta"><ElTag>{{ categoryLabel }}</ElTag><ElTag type="info">{{ typeNames[resource.display_type || resource.resource_type] }}</ElTag><ElTag type="warning">{{ difficultyNames[resource.difficulty] }}</ElTag></div>
        <div class="resource-tags"><ElTag v-for="tag in resource.tags" :key="tag">{{ tag }}</ElTag></div>
        <div v-if="resource.status === 'published'" class="learning-actions">
          <ElButton type="primary" :disabled="!state.stateReady || !courseReady || state.busy || !!state.pending" @click="router.push({name:'course-learning',params:{id:resource.id}})">{{course?.chapters.length ? courseButton(progress) : progress==='not_started'?'开始学习':'进入课程学习'}}</ElButton>
          <ElTag v-if="progress === 'completed'" type="success">已完成学习</ElTag>
          <ElButton :disabled="!state.stateReady || state.busy || !!state.pending" @click="controller?.perform(state.favorite ? 'unfavorite' : 'favorite')">{{ state.favorite ? '取消收藏' : '收藏资源' }}</ElButton>
          <ElButton v-if="state.pending" :disabled="state.busy || !state.stateReady" @click="controller?.perform(state.pending.action as 'start' | 'complete' | 'favorite' | 'unfavorite')">重试原操作</ElButton>
        </div>
          </div>
        </header>
        <div class="detail-notices">
        <ElAlert v-if="courseError" :title="courseError" type="warning" :closable="false" />
        <ElButton v-if="courseError" @click="load">重新加载课程状态</ElButton>
        <ElAlert v-if="state.stateError" :title="state.stateError" type="warning" :closable="false" />
        <ElButton v-if="!state.stateReady" :disabled="state.busy" @click="refreshState">重新查询状态</ElButton>
        <ElAlert v-if="state.viewError" :title="state.viewError" type="warning" :closable="false" />
        <ElButton v-if="state.viewError" @click="controller?.recordView()">重试浏览记录</ElButton>
        <ElAlert v-if="state.actionError" :title="state.actionError" type="error" :closable="false" role="alert" />
        <ElAlert v-if="state.notice" :title="state.notice" type="success" :closable="false" />
        </div>
        <div class="detail-layout">
          <section class="detail-body" aria-label="学习内容">
        <h2>学习内容</h2><div v-if="resource.content" class="resource-content">{{ resource.content }}</div><p v-else>请通过原资源地址查看学习内容。</p>
        <a v-if="contentUrl" :href="contentUrl" target="_blank" rel="noopener noreferrer" class="source-link">打开原资源 ↗</a>
          </section>
          <aside class="detail-sidebar" aria-label="学习概况">
            <div class="detail-status"><p class="detail-eyebrow">学习概况</p><h2>按自己的节奏学习</h2>
              <dl class="user-details">
          <dt>学习状态</dt><dd>{{ state.stateReady && courseReady ? progressNames[progress] : '待确认' }}<template v-if="courseReady && course?.chapters.length"> · 章节完成 {{ percent }}%</template></dd>
          <dt>收藏状态</dt><dd>{{ state.stateReady ? state.favorite ? '已收藏' : '未收藏' : '待确认' }}</dd>
              </dl>
              <progress v-if="state.stateReady && courseReady && course?.chapters.length" :value="percent" max="100" :aria-label="'章节完成 ' + percent + '%'" />
              <p class="detail-hint">进入课程后可查看章节内容，学习完成情况以已记录的状态为准。</p>
            </div>
            <details class="detail-metadata"><summary>资源信息</summary>
        <dl class="user-details">
          <dt>资源编号</dt><dd>{{ resource.id }}</dd><dt>资源状态</dt><dd>{{ resource.status }}</dd>
          <dt>来源</dt><dd>{{ resource.source_name || '未提供' }}</dd><dt>许可说明</dt><dd>{{ resource.license_note || '未提供' }}</dd>
          <dt>版本</dt><dd>{{ resource.version_no }}</dd><dt>创建者编号</dt><dd>{{ resource.created_by }}</dd>
          <dt>发布时间</dt><dd>{{ formatTime(resource.published_at) }}</dd><dt>创建时间</dt><dd>{{ formatTime(resource.created_at) }}</dd><dt>更新时间</dt><dd>{{ formatTime(resource.updated_at) }}</dd>
        </dl>
            </details>
          </aside>
        </div>
      </article>
    </template>
  </section>
</template>

<style scoped>
.resource-detail-page{min-width:0}.resource-detail{padding:0;overflow:hidden;border-color:#e6dfd8}.detail-hero{display:grid;grid-template-columns:38% minmax(0,1fr);background:#fff;border-bottom:1px solid #e6dfd8}.detail-cover{padding:28px;background:#f5f0e8;display:flex;align-items:center}.detail-cover :deep(.resource-cover){width:100%;border:1px solid #e6dfd8;border-radius:10px}.detail-intro{padding:32px;min-width:0}.detail-eyebrow{font-size:11px;font-weight:600;letter-spacing:2px;color:#a9583e;margin:0 0 12px}.detail-intro h1{font-size:27px;line-height:1.5;margin:0 0 12px;overflow-wrap:anywhere}.detail-intro>p:not(.detail-eyebrow){font-size:14px;margin:0 0 18px;line-height:1.85}.detail-intro .resource-meta,.detail-intro .resource-tags{margin:10px 0}.detail-intro .learning-actions{margin:22px 0 0}.learning-actions{align-items:center}.learning-actions .el-button{max-width:100%;white-space:normal;height:auto;min-height:40px}.detail-notices{padding:0 28px}.detail-layout{display:grid;grid-template-columns:minmax(0,1fr) 290px;gap:32px;padding:32px}.detail-body{min-width:0}.detail-body h2{margin:0 0 20px;font-size:21px;padding-bottom:14px;border-bottom:1px solid #e6dfd8;color:#292720}.detail-body .resource-content{font-size:15px;line-height:2;color:#56534c}.detail-body .source-link{font-size:13px}.detail-sidebar{min-width:0}.detail-status{padding:20px;background:#faf9f5;border:1px solid #e6dfd8;border-radius:10px}.detail-status h2{font-size:16px;margin:0 0 20px;color:#292720}.detail-sidebar .user-details{grid-template-columns:64px minmax(0,1fr);gap:12px;font-size:12px;margin:16px 0}.detail-sidebar progress{display:block;width:100%;height:5px;border:0;border-radius:5px;overflow:hidden;appearance:none;accent-color:#a9583e;background:#e6dfd8}.detail-sidebar progress::-webkit-progress-bar{background:#e6dfd8}.detail-sidebar progress::-webkit-progress-value{background:#a9583e}.detail-sidebar progress::-moz-progress-bar{background:#a9583e}.detail-hint{font-size:12px;line-height:1.8;margin:16px 0 0;color:#77736b}.detail-metadata{margin-top:16px;padding:16px 20px;border:1px solid #e6dfd8;border-radius:10px}.detail-metadata summary{cursor:pointer;font-size:13px;color:#56534c;font-weight:600}.detail-metadata summary:focus-visible{outline:2px solid #a9583e;outline-offset:4px}
@media(max-width:800px){.detail-hero{grid-template-columns:minmax(0,1fr)}.detail-cover{padding:20px}.detail-cover :deep(.resource-cover){max-width:460px;margin:0 auto}.detail-layout{grid-template-columns:minmax(0,1fr);padding:24px;gap:24px}.detail-intro{padding:24px}.detail-sidebar{display:grid;grid-template-columns:1fr 1fr;gap:16px;align-items:start}.detail-metadata{margin-top:0}}
@media(max-width:600px){.detail-intro h1{font-size:24px}.detail-sidebar{grid-template-columns:minmax(0,1fr)}.detail-layout,.detail-intro{padding:20px}.detail-cover{padding:16px}.detail-notices{padding:0 20px}.detail-intro .learning-actions{gap:10px}.detail-body .resource-content{font-size:14px}}
</style>
