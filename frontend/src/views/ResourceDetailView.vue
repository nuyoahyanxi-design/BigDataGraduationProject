<script setup lang="ts">
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
  <section>
    <ElButton @click="router.push({ name: 'resources' })">返回资源列表</ElButton>
    <ElAlert v-if="invalidId" title="资源编号无效" type="error" :closable="false" />
    <p v-else-if="state?.loading" role="status">正在加载详情…</p>
    <template v-else-if="state">
      <ElAlert v-if="state.error" :title="state.error" type="error" :closable="false" role="alert" />
      <ElButton v-if="state.error" @click="load">重新加载</ElButton>
      <article v-if="resource" class="panel resource-detail">
        <h1>{{ resource.title }}</h1><p>{{ resource.summary }}</p>
        <div class="resource-meta"><ElTag>{{ categoryLabel }}</ElTag><ElTag type="info">{{ typeNames[resource.resource_type] }}</ElTag><ElTag type="warning">{{ difficultyNames[resource.difficulty] }}</ElTag></div>
        <div class="resource-tags"><ElTag v-for="tag in resource.tags" :key="tag">{{ tag }}</ElTag></div>
        <dl class="user-details">
          <dt>资源编号</dt><dd>{{ resource.id }}</dd><dt>资源状态</dt><dd>{{ resource.status }}</dd>
          <dt>来源</dt><dd>{{ resource.source_name || '未提供' }}</dd><dt>许可说明</dt><dd>{{ resource.license_note || '未提供' }}</dd>
          <dt>版本</dt><dd>{{ resource.version_no }}</dd><dt>创建者编号</dt><dd>{{ resource.created_by }}</dd>
          <dt>发布时间</dt><dd>{{ formatTime(resource.published_at) }}</dd><dt>创建时间</dt><dd>{{ formatTime(resource.created_at) }}</dd><dt>更新时间</dt><dd>{{ formatTime(resource.updated_at) }}</dd>
          <dt>学习状态</dt><dd>{{ state.stateReady && courseReady ? progressNames[progress] : '待确认' }}<template v-if="courseReady && course?.chapters.length"> · 章节完成 {{ percent }}%</template></dd>
          <dt>收藏状态</dt><dd>{{ state.stateReady ? state.favorite ? '已收藏' : '未收藏' : '待确认' }}</dd>
        </dl>
        <ElAlert v-if="courseError" :title="courseError" type="warning" :closable="false" />
        <ElButton v-if="courseError" @click="load">重新加载课程状态</ElButton>
        <ElAlert v-if="state.stateError" :title="state.stateError" type="warning" :closable="false" />
        <ElButton v-if="!state.stateReady" :disabled="state.busy" @click="refreshState">重新查询状态</ElButton>
        <ElAlert v-if="state.viewError" :title="state.viewError" type="warning" :closable="false" />
        <ElButton v-if="state.viewError" @click="controller?.recordView()">重试浏览记录</ElButton>
        <ElAlert v-if="state.actionError" :title="state.actionError" type="error" :closable="false" role="alert" />
        <ElAlert v-if="state.notice" :title="state.notice" type="success" :closable="false" />
        <div v-if="resource.status === 'published'" class="learning-actions">
          <ElButton type="primary" :disabled="!state.stateReady || !courseReady || state.busy || !!state.pending" @click="router.push({name:'course-learning',params:{id:resource.id}})">{{course?.chapters.length ? courseButton(progress) : progress==='not_started'?'开始学习':'进入课程学习'}}</ElButton>
          <ElTag v-if="progress === 'completed'" type="success">已完成学习</ElTag>
          <ElButton :disabled="!state.stateReady || state.busy || !!state.pending" @click="controller?.perform(state.favorite ? 'unfavorite' : 'favorite')">{{ state.favorite ? '取消收藏' : '收藏资源' }}</ElButton>
          <ElButton v-if="state.pending" :disabled="state.busy || !state.stateReady" @click="controller?.perform(state.pending.action as 'start' | 'complete' | 'favorite' | 'unfavorite')">重试原操作</ElButton>
        </div>
        <h2>学习内容</h2><div v-if="resource.content" class="resource-content">{{ resource.content }}</div><p v-else>请通过原资源地址查看学习内容。</p>
        <a v-if="contentUrl" :href="contentUrl" target="_blank" rel="noopener noreferrer" class="source-link">打开原资源 ↗</a>
      </article>
    </template>
  </section>
</template>
