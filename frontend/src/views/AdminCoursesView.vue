<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElAlert, ElButton, ElEmpty, ElInput, ElOption, ElPagination, ElSelect, ElTag } from 'element-plus'
import { AdminCourses } from '@/services/admin-courses'
import { statusNames, utcTime } from '@/types/admin'
const router=useRouter(),controller=new AdminCourses(),state=controller.state
function search(){state.page=1;void controller.load()}
onMounted(()=>void controller.load())
</script>
<template>
  <section class="admin-courses"><header><RouterLink to="/admin">返回管理员后台</RouterLink><h1>课程管理</h1><p>创建课程、维护章节和发布课程。隐藏课程不会删除已有学习记录，也不会自动触发Spark重算。</p></header>
    <ElAlert v-if="state.error" :title="state.error" type="error" :closable="false" role="alert" />
    <ElAlert v-if="state.notice" :title="state.notice" type="success" :closable="false" role="status" />
    <div class="admin-toolbar"><ElInput v-model="state.query" aria-label="课程标题搜索" placeholder="搜索课程标题" maxlength="200" clearable @keyup.enter="search" />
      <ElSelect v-model="state.status" aria-label="课程状态筛选"><ElOption label="全部状态" value="all" /><ElOption label="草稿" value="draft" /><ElOption label="已发布" value="published" /><ElOption label="已隐藏" value="offline" /></ElSelect>
      <ElButton :disabled="state.loading || state.busy" @click="search">搜索课程</ElButton><ElButton :disabled="state.loading || state.busy" @click="controller.load()">刷新列表</ElButton><ElButton type="primary" :disabled="state.busy || state.loading" @click="router.push({name:'admin-course-create'})">创建课程</ElButton>
    </div>
    <p v-if="state.loading" role="status">正在读取课程…</p>
    <ElEmpty v-else-if="!state.list?.items.length" description="暂无匹配课程" />
    <div v-else class="course-list"><article v-for="row in state.list.items" :key="row.id" class="panel course-row"><div><h2>{{row.title}} <ElTag>{{row.status==='offline'?'已隐藏':statusNames[row.status]}}</ElTag></h2><p>{{row.summary}}</p><small>课程编号 {{row.id}} · 章节数量 {{row.chapter_count ?? 0}} · 更新时间 {{utcTime(row.updated_at)}}</small></div><div class="course-buttons">
      <ElButton :disabled="state.busy || state.loading" @click="router.push({name:'admin-course-edit',params:{id:row.id}})">编辑课程</ElButton><ElButton type="primary" :disabled="state.busy || state.loading" @click="router.push({name:'admin-course-chapters',params:{id:row.id}})">管理章节</ElButton>
    </div></article></div>
    <ElPagination v-if="state.list && state.list.total>10" v-model:current-page="state.page" :disabled="state.busy || state.loading" :page-size="10" :total="state.list.total" layout="prev,pager,next,total" @current-change="controller.load()" />
  </section>
</template>
<style scoped>
.admin-courses{max-width:1100px;margin:auto}.course-row{display:flex;justify-content:space-between;gap:24px;align-items:center}.course-row h2{font-size:18px;margin-top:0}.course-buttons{display:flex;gap:8px;flex-wrap:wrap}.course-buttons .el-button{margin-left:0}.editor{margin-top:24px}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}.chapter-list{padding:0;list-style:none}.chapter-list li{display:flex;justify-content:space-between;align-items:center;gap:20px;border-bottom:1px solid #e5e7eb;padding:18px 0}.chapter-list small{display:block;color:#64748b;margin-top:8px;overflow-wrap:anywhere}.delete-confirm{padding:18px;border:1px solid #fca5a5;border-radius:8px;margin-top:16px;background:#fff7f7}@media(max-width:700px){.course-row,.chapter-list li{flex-direction:column;align-items:stretch}.form-grid{grid-template-columns:1fr}}
</style>
