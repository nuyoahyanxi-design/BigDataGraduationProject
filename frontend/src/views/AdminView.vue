<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElAlert, ElButton, ElDialog, ElEmpty, ElForm, ElFormItem, ElInput, ElOption, ElPagination, ElSelect, ElTable, ElTableColumn, ElTabPane, ElTabs, ElTag } from 'element-plus'
import { listAdminUsers, getAdminBatches, listAdminResources, createResource, updateResource, changeResourceStatus } from '@/api/admin'
import { getResource } from '@/api/resources'
import { resourceError } from '@/services/resource-learning'
import { categories, typeNames, difficultyNames } from '@/types/resources'
import type { Page, ResourceSummary } from '@/types/resources'
import { controlledTags, statusNames, newResource, resourcePayload, validateResource, utcTime } from '@/types/admin'
import type { AdminUser, BatchList } from '@/types/admin'
const tab=ref('resources'), users=ref<Page<AdminUser>>(), resources=ref<Page<ResourceSummary>>(), batches=ref<BatchList>()
const userPage=ref(1), resourcePage=ref(1), query=ref(''), filterStatus=ref('all')
const userError=ref(''), resourceErr=ref(''), batchError=ref(''), notice=ref('')
const userLoading=ref(false), resourceLoading=ref(false), batchLoading=ref(false), busy=ref(false)
async function loadUsers(){ if(userLoading.value)return; userLoading.value=true; userError.value=''; users.value=undefined; try{users.value=await listAdminUsers(userPage.value)}catch(e){userError.value=resourceError(e)}finally{userLoading.value=false} }
async function loadResources(){ if(resourceLoading.value)return; resourceLoading.value=true; resourceErr.value=''; resources.value=undefined; try{resources.value=await listAdminResources(resourcePage.value,query.value,filterStatus.value)}catch(e){resourceErr.value=resourceError(e)}finally{resourceLoading.value=false} }
async function loadBatches(){ if(batchLoading.value)return; batchLoading.value=true; batchError.value=''; batches.value=undefined; try{batches.value=await getAdminBatches()}catch(e){batchError.value=resourceError(e)}finally{batchLoading.value=false} }
function search(){ resourcePage.value=1; void loadResources() }
const editor=ref(false), editingId=ref<number|null>(null), form=ref(newResource()), formError=ref('')
function add(){if(busy.value)return; editingId.value=null; form.value=newResource(); formError.value=''; editor.value=true}
async function edit(row:ResourceSummary){
  if(busy.value)return; busy.value=true; notice.value=''; resourceErr.value=''
  try{const detail=await getResource(row.id); editingId.value=row.id; form.value=resourcePayload(detail); formError.value=''; editor.value=true}
  catch(e){resourceErr.value=resourceError(e)}finally{busy.value=false}
}
async function save(){
  if(busy.value)return; formError.value=validateResource(form.value); if(formError.value)return
  busy.value=true
  try{const result=editingId.value===null?await createResource(resourcePayload(form.value)):await updateResource(editingId.value,resourcePayload(form.value)); editor.value=false; notice.value=`资源“${result.title}”已保存（${statusNames[result.status]}）`; await loadResources()}
  catch(e){formError.value=resourceError(e)}finally{busy.value=false}
}
const statusTarget=ref<ResourceSummary|null>(null), statusError=ref('')
function askStatus(row:ResourceSummary){if(busy.value)return; statusError.value=''; statusTarget.value=row}
async function confirmStatus(){
  const target=statusTarget.value; if(!target||busy.value)return; busy.value=true
  try{const result=await changeResourceStatus(target.id,target.status==='published'?'offline':'published'); statusTarget.value=null; notice.value=`资源“${result.title}”${statusNames[result.status]}`; await loadResources()}
  catch(e){statusError.value=resourceError(e)}finally{busy.value=false}
}
function closeEditor(done:()=>void){if(!busy.value)done()}
onMounted(()=>{void loadUsers();void loadResources();void loadBatches()})
</script>
<template>
  <section><h1>管理员后台</h1><RouterLink to="/admin/courses">进入课程与章节管理</RouterLink><p>用户只读查看 · 资源维护 · Spark最近发布批次。资源保存不自动触发离线重算。</p>
    <ElAlert v-if="notice" :title="notice" type="success" :closable="false" role="status" />
    <ElTabs v-model="tab">
      <ElTabPane label="资源管理" name="resources">
        <div class="admin-toolbar"><ElInput v-model="query" placeholder="搜索资源标题" maxlength="200" clearable @keyup.enter="search" />
          <ElSelect v-model="filterStatus" aria-label="资源状态筛选"><ElOption label="全部状态" value="all" /><ElOption label="草稿" value="draft" /><ElOption label="已发布" value="published" /><ElOption label="已下架" value="offline" /></ElSelect>
          <ElButton :disabled="resourceLoading || busy" @click="search">搜索</ElButton><ElButton type="primary" :disabled="busy" @click="add">新增资源</ElButton></div>
        <p v-if="resourceLoading" role="status">正在读取资源…</p><ElAlert v-else-if="resourceErr" :title="resourceErr" type="error" :closable="false" /><ElEmpty v-else-if="!resources?.items.length" description="暂无匹配资源" />
        <ElTable v-else :data="resources.items" row-key="id"><ElTableColumn prop="id" label="ID" width="80" /><ElTableColumn prop="title" label="标题" min-width="200" /><ElTableColumn label="状态" width="110"><template #default="scope"><ElTag>{{statusNames[scope.row.status as keyof typeof statusNames]}}</ElTag></template></ElTableColumn><ElTableColumn prop="version_no" label="版本" width="80" /><ElTableColumn label="操作" width="190"><template #default="scope"><ElButton :disabled="busy" @click="edit(scope.row as ResourceSummary)">编辑</ElButton><ElButton :disabled="busy" @click="askStatus(scope.row as ResourceSummary)">{{scope.row.status==='published'?'下架':'发布'}}</ElButton></template></ElTableColumn></ElTable>
        <ElPagination v-if="resources && resources.total>10" v-model:current-page="resourcePage" :disabled="resourceLoading || busy" :page-size="10" :total="resources.total" layout="prev,pager,next,total" @current-change="loadResources" />
        <ElButton :disabled="resourceLoading" @click="loadResources">刷新资源</ElButton>
      </ElTabPane>
      <ElTabPane label="用户查看" name="users"><ElButton :disabled="userLoading" @click="loadUsers">刷新用户</ElButton><p v-if="userLoading" role="status">正在读取用户…</p><ElAlert v-else-if="userError" :title="userError" type="error" :closable="false" /><ElEmpty v-else-if="!users?.items.length" description="暂无用户" />
        <ElTable v-else :data="users.items" row-key="id"><ElTableColumn prop="username" label="用户名" /><ElTableColumn label="角色"><template #default="scope">{{scope.row.role==='admin'?'管理员':'学习者'}}</template></ElTableColumn><ElTableColumn prop="status" label="状态" /><ElTableColumn label="创建时间" min-width="220"><template #default="scope">{{utcTime(scope.row.created_at)}}</template></ElTableColumn></ElTable>
        <ElPagination v-if="users && users.total>20" v-model:current-page="userPage" :disabled="userLoading" :page-size="20" :total="users.total" layout="prev,pager,next,total" @current-change="loadUsers" />
      </ElTabPane>
      <ElTabPane label="Spark批次" name="batches"><ElButton :disabled="batchLoading" @click="loadBatches">刷新批次</ElButton><p v-if="batchLoading" role="status">正在读取发布记录…</p><ElAlert v-else-if="batchError" :title="batchError" type="error" :closable="false" /><template v-else><p>{{batches?.scope}}</p><ElEmpty v-if="!batches?.items.length" description="暂无发布记录" /><article v-for="row in batches?.items" :key="row.stage" class="panel admin-batch"><h2>{{row.stage}} <ElTag>{{row.status}}</ElTag></h2><dl class="user-details"><dt>批次编号</dt><dd>{{row.batch_id || '尚未发布'}}</dd><dt>生成时间</dt><dd>{{utcTime(row.generated_at)}}</dd><dt>快照截止</dt><dd>{{utcTime(row.as_of_utc)}}</dd><dt>数据量</dt><dd>{{row.data_count===null?'未知':row.data_count}} · {{row.count_label}}</dd><dt>来源</dt><dd>{{row.source}}</dd></dl><p v-if="row.message">{{row.message}}</p></article></template></ElTabPane>
    </ElTabs>
    <ElDialog v-model="editor" :title="editingId===null?'新增资源':'编辑资源'" width="min(760px,95vw)" :close-on-click-modal="false" :close-on-press-escape="!busy" :show-close="!busy" :before-close="closeEditor">
      <ElAlert v-if="formError" :title="formError" type="error" :closable="false" role="alert" />
      <ElForm label-position="top" :disabled="busy">
        <ElFormItem label="标题（必填）"><ElInput v-model="form.title" aria-label="资源标题" maxlength="200" /></ElFormItem>
        <ElFormItem label="简介（必填）"><ElInput v-model="form.summary" aria-label="资源简介" type="textarea" maxlength="1000" /></ElFormItem>
        <ElFormItem label="分类"><ElSelect v-model="form.category_code" aria-label="资源分类"><ElOption v-for="[code,name] in categories" :key="code" :value="code" :label="name" /></ElSelect></ElFormItem>
        <ElFormItem label="类型"><ElSelect v-model="form.resource_type" aria-label="资源类型"><ElOption v-for="(name,code) in typeNames" :key="code" :value="code" :label="name" /></ElSelect></ElFormItem>
        <ElFormItem label="受控标签（发布时必填）"><ElSelect v-model="form.tags" multiple aria-label="资源标签"><ElOption v-for="tag in controlledTags" :key="tag" :value="tag" :label="tag" /></ElSelect></ElFormItem>
        <ElFormItem label="难度"><ElSelect v-model="form.difficulty" aria-label="资源难度"><ElOption v-for="level in [1,2,3]" :key="level" :value="level" :label="difficultyNames[level]" /></ElSelect></ElFormItem>
        <ElFormItem label="正文（发布时正文或外链至少一项）"><ElInput v-model="form.content" aria-label="资源正文" type="textarea" :rows="4" maxlength="100000" /></ElFormItem>
        <ElFormItem label="公开HTTP/HTTPS外链"><ElInput v-model="form.content_url" aria-label="资源外链" maxlength="1000" /></ElFormItem>
        <ElFormItem label="来源名称"><ElInput v-model="form.source_name" aria-label="资源来源" maxlength="255" /></ElFormItem>
        <ElFormItem label="许可说明"><ElInput v-model="form.license_note" aria-label="许可说明" maxlength="500" /></ElFormItem>
      </ElForm><template #footer><ElButton :disabled="busy" @click="editor=false">取消</ElButton><ElButton type="primary" :loading="busy" @click="save">保存资源</ElButton></template>
    </ElDialog>
    <ElDialog :model-value="statusTarget!==null" title="确认资源状态变更" width="min(500px,95vw)" :show-close="!busy" :close-on-press-escape="!busy" :close-on-click-modal="false" @update:model-value="value=>{if(!value && !busy)statusTarget=null}">
      <p>确认{{statusTarget?.status==='published'?'下架':'发布'}}资源“{{statusTarget?.title}}”？</p><ElAlert v-if="statusError" :title="statusError" type="error" :closable="false" /><template #footer><ElButton :disabled="busy" @click="statusTarget=null">取消变更</ElButton><ElButton type="primary" :loading="busy" @click="confirmStatus">确认变更</ElButton></template>
    </ElDialog>
  </section>
</template>

