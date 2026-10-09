<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElAlert, ElButton, ElEmpty } from 'element-plus'
import { AdminCourses } from '@/services/admin-courses'
import { adminResourceId } from '@/services/admin-course-navigation'
const route=useRoute(),router=useRouter(),controller=shallowRef(new AdminCourses())
const state=computed(()=>controller.value.state)
async function load(){const owner=new AdminCourses();controller.value=owner;const id=adminResourceId(route.params.id);if(!id){owner.state.error='课程编号无效';return}await owner.select(id)}
function add(){const id=state.value.course?.resource_id;if(id)void router.push({name:'admin-chapter-create',params:{courseId:id}})}
watch(()=>route.params.id,load,{immediate:true})
</script>
<template>
  <section class="admin-chapter-list"><ElButton @click="router.push({name:'admin-courses'})">返回课程列表</ElButton>
    <header class="page-header"><p>课程管理 / 章节管理</p><h1>{{state.course?.title || '章节管理'}}</h1><p>按排序展示章节。已有章节学习记录的课程不能新增、删除或重排章节，原学习进度不会被清空。</p></header>
    <ElAlert v-if="state.error" :title="state.error" type="error" :closable="false" role="alert" />
    <ElAlert v-if="state.notice" :title="state.notice" type="success" :closable="false" role="status" />
    <p v-if="state.loading" role="status">正在读取章节列表…</p><ElButton v-if="!state.course && !state.loading" @click="load">重新加载章节列表</ElButton>
    <template v-if="state.course"><div class="chapter-toolbar"><span>章节数量 {{state.course.chapters.length}}</span><ElButton type="primary" :disabled="state.busy || state.loading" @click="add">新增章节</ElButton></div>
      <ElEmpty v-if="!state.course.chapters.length" description="暂无章节，可创建第一章" />
      <ol class="chapter-list"><li v-for="chapter in state.course.chapters" :key="chapter.id" class="panel"><div class="chapter-row"><div><h2>{{chapter.title}}</h2><p>排序号 {{chapter.position}}</p><p class="video-address">视频地址：{{chapter.video_url || '未配置视频'}}</p></div><div class="course-buttons"><ElButton :disabled="state.busy || state.loading" @click="router.push({name:'admin-chapter-edit',params:{courseId:state.course.resource_id,chapterId:chapter.id}})">编辑章节</ElButton><ElButton type="danger" :disabled="state.busy || state.loading" @click="controller.askDelete(chapter)">删除章节</ElButton></div></div>
        <div v-if="state.deleteTarget?.id===chapter.id" class="delete-confirm" role="alert"><p>确认删除“{{chapter.title}}”？此操作不可恢复；已有学习记录的课程将被拒绝删除。</p><ElButton :disabled="state.busy" @click="state.deleteTarget=null">取消删除</ElButton><ElButton type="danger" :loading="state.busy" @click="controller.confirmDelete()">确认删除章节</ElButton></div>
      </li></ol>
    </template>
  </section>
</template>
<style scoped>
.admin-chapter-list{max-width:1100px;margin:auto}.page-header{margin:20px 0}.page-header p{color:#64748b;line-height:1.7}.chapter-toolbar{display:flex;justify-content:space-between;align-items:center;margin:24px 0}.chapter-list{padding:0;list-style:none}.chapter-row{display:flex;justify-content:space-between;align-items:center;gap:24px}.chapter-row h2{font-size:18px;margin-top:0}.video-address{overflow-wrap:anywhere;color:#64748b}.course-buttons{display:flex;gap:8px;flex-wrap:wrap}.course-buttons .el-button{margin-left:0}.delete-confirm{margin-top:16px;padding:16px;border:1px solid #fca5a5;border-radius:8px;background:#fff7f7}@media(max-width:700px){.chapter-row{flex-direction:column;align-items:stretch}.panel{padding:18px}.course-buttons .el-button{flex:1}}
</style>
