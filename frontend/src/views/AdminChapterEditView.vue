<script setup lang="ts">
import { computed, shallowRef, ref, watch, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElAlert, ElButton, ElForm, ElFormItem, ElInput, ElInputNumber } from 'element-plus'
import { AdminCourses } from '@/services/admin-courses'
import { adminResourceId } from '@/services/admin-course-navigation'
const route=useRoute(),router=useRouter(),controller=shallowRef(new AdminCourses())
const state=computed(()=>controller.value.state),ready=ref(false)
const creating=computed(()=>route.name==='admin-chapter-create')
let active=true
onUnmounted(()=>{active=false})
function back(){const id=adminResourceId(route.params.courseId);void router.push(id?{name:'admin-course-chapters',params:{id}}:{name:'admin-courses'})}
async function load(){
  const owner=new AdminCourses();controller.value=owner;ready.value=false
  const id=adminResourceId(route.params.courseId),chapterId=adminResourceId(route.params.chapterId)
  if(!id || (!creating.value && !chapterId)){owner.state.error='课程或章节编号无效';return}
  await owner.select(id)
  if(!active || owner!==controller.value || !owner.state.course)return
  const chapter=creating.value?undefined:owner.state.course.chapters.find(ch=>ch.id===chapterId)
  if(!creating.value && !chapter){owner.state.error='章节不存在或不属于当前课程';return}
  owner.editChapter(chapter);ready.value=true
  if(route.query.saved==='1')owner.state.notice='章节已保存'
}
async function save(){
  if(!ready.value)return
  const owner=controller.value,result=await owner.saveChapter()
  if(!result || !active || owner!==controller.value)return
  if(creating.value)await router.replace({name:'admin-chapter-edit',params:{courseId:result.resource_id,chapterId:result.id},query:{saved:'1'}})
  else owner.editChapter(owner.state.course?.chapters.find(ch=>ch.id===result.id))
}
watch(()=>[route.name,route.params.courseId,route.params.chapterId],load,{immediate:true})
</script>
<template>
  <section class="admin-editor-page"><ElButton :disabled="state.busy" @click="back">返回章节列表</ElButton>
    <header class="page-header"><p>课程管理 / 章节管理 / {{creating?'新增章节':'编辑章节'}}</p><h1>{{creating?'新增章节':'编辑章节内容'}}</h1><p v-if="state.course">课程：{{state.course.title}}</p><p>教学内容独立编辑。已有学习记录的章节可修订内容，但不能更改目录排序；保存不会清空学习进度。</p></header>
    <ElAlert v-if="state.error" :title="state.error" type="error" :closable="false" role="alert" />
    <ElAlert v-if="state.notice" :title="state.notice" type="success" :closable="false" role="status" />
    <p v-if="state.loading" role="status">正在读取章节…</p><ElButton v-if="!ready && !state.loading" @click="load">重新加载章节</ElButton>
    <article v-if="ready" class="panel">
<ElForm label-position="top" :disabled="state.busy">
        <div class="form-grid"><ElFormItem label="章节标题"><ElInput v-model="state.chapterForm.title" aria-label="章节标题" maxlength="200" /></ElFormItem><ElFormItem label="排序（1–1000，不重复）"><ElInputNumber v-model="state.chapterForm.position" aria-label="章节排序" :min="1" :max="1000" :precision="0" /></ElFormItem></div>
        <ElFormItem label="视频URL（本地静态文件，无视频上传）"><ElInput v-model="state.chapterForm.video_url" aria-label="章节视频URL" placeholder="/demo/video.mp4 或 /videos/lesson.mp4" maxlength="500" /></ElFormItem>
        <ElFormItem label="知识点（以逗号分隔）"><ElInput v-model="state.chapterForm.knowledge_tags" aria-label="章节知识点" /></ElFormItem>
        <ElFormItem label="教学目标（每行一项，最多8项）"><ElInput v-model="state.chapterForm.learning_objectives" aria-label="章节教学目标" type="textarea" :rows="3" /></ElFormItem>
        <ElFormItem label="Markdown正文（必填）"><ElInput v-model="state.chapterForm.content" aria-label="章节Markdown正文" type="textarea" :rows="12" maxlength="100000" /></ElFormItem>
        <ElFormItem label="示例代码（只保存，不执行）"><ElInput v-model="state.chapterForm.example_code" aria-label="章节示例代码" type="textarea" :rows="6" maxlength="10000" /></ElFormItem>
        <ElFormItem label="章节练习（每行一项，最多8项）"><ElInput v-model="state.chapterForm.exercises" aria-label="章节练习" type="textarea" :rows="3" /></ElFormItem>
      </ElForm><div class="course-buttons"><ElButton :disabled="state.busy" @click="back()">返回章节列表</ElButton><ElButton type="primary" :loading="state.busy" :disabled="state.loading || !ready" @click="save">保存章节</ElButton></div>
    </article>
  </section>
</template>
<style scoped>
.admin-editor-page{max-width:900px;margin:auto}.page-header{margin:20px 0}.page-header h1{font-size:26px;margin-bottom:8px}.page-header p{color:#64748b;line-height:1.7}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}.course-buttons{display:flex;gap:12px;flex-wrap:wrap;margin-top:24px;padding-top:20px;border-top:1px solid #e5e7eb}.course-buttons .el-button{margin-left:0}@media(max-width:700px){.form-grid{grid-template-columns:1fr}.page-header h1{font-size:22px}.panel{padding:18px}.course-buttons .el-button{flex:1}}
</style>
