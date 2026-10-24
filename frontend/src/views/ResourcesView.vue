<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElAlert, ElButton, ElCard, ElEmpty, ElInput, ElOption, ElPagination, ElSelect, ElTag } from 'element-plus'
import { listResources } from '@/api/resources'
import ResourceCover from '@/components/ResourceCover.vue'
import { resourceError } from '@/services/resource-learning'
import { categories, typeNames, difficultyNames, type ResourceSummary } from '@/types/resources'
const router = useRouter()
const title = ref(''), category = ref(''), search = ref('')
const page = ref(1), pageSize = ref(12), total = ref(0)
const items = ref<ResourceSummary[]>([]), loading = ref(false), errorMessage = ref('')
let requestNumber = 0
async function load() {
  const number = ++requestNumber
  loading.value = true; errorMessage.value = ''
  try {
    const result = await listResources({ page: page.value, page_size: pageSize.value,
      ...(search.value ? { q: search.value } : {}), ...(category.value ? { category_code: category.value } : {}) })
    if (number !== requestNumber) return
    items.value = result.items; total.value = result.total
  } catch (error) { if (number === requestNumber) { items.value = []; total.value = 0; errorMessage.value = resourceError(error) } }
  finally { if (number === requestNumber) loading.value = false }
}
function applyFilters() { search.value = title.value.trim(); page.value = 1; void load() }
function changePage(value: number) { page.value = value; void load() }
function changeSize(value: number) { pageSize.value = value; page.value = 1; void load() }
onMounted(load)
</script>
<template>
  <section>
    <div class="page-heading"><h1>学习资源</h1><span>共 {{ total }} 项</span></div>
    <form class="resource-filters" @submit.prevent="applyFilters">
      <ElInput v-model="title" aria-label="标题搜索" placeholder="搜索资源标题" maxlength="200" clearable :disabled="loading" />
      <ElSelect v-model="category" aria-label="分类筛选" placeholder="全部分类" clearable :disabled="loading" @change="applyFilters">
        <ElOption v-for="[value, label] in categories" :key="value" :label="label" :value="value" />
      </ElSelect>
      <ElButton type="primary" native-type="submit" :loading="loading">搜索</ElButton>
    </form>
    <ElAlert v-if="errorMessage" :title="errorMessage" type="error" :closable="false" role="alert" />
    <ElButton v-if="errorMessage" @click="load">重新加载</ElButton>
    <p v-if="loading" role="status">正在加载资源…</p>
    <ElEmpty v-else-if="!errorMessage && !items.length" description="没有符合条件的资源" />
    <div v-else-if="!errorMessage" class="resource-grid">
      <ElCard v-for="item in items" :key="item.id" class="resource-card resource-card--illustrated" shadow="never">
        <ResourceCover :resource-id="item.id" />
        <h2>{{ item.title }}</h2><p class="resource-summary">{{ item.summary }}</p>
        <div class="resource-meta"><ElTag type="info">{{ typeNames[item.display_type || item.resource_type] }}</ElTag><ElTag type="warning">{{ difficultyNames[item.difficulty] }}</ElTag></div>
        <div class="resource-tags"><ElTag v-for="tag in item.tags" :key="tag" size="small">{{ tag }}</ElTag></div>
        <ElButton @click="router.push({ name: 'resource-detail', params: { id: item.id } })">查看详情</ElButton>
      </ElCard>
    </div>
    <ElPagination v-if="!errorMessage && total > 0" class="resource-pagination" :current-page="page" :page-size="pageSize" :total="total"
      :page-sizes="[12, 24, 48]" layout="total, sizes, prev, pager, next" :disabled="loading" @current-change="changePage" @size-change="changeSize" />
  </section>
</template>
