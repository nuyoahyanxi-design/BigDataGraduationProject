<script setup lang="ts">
import { computed, shallowRef, ref, watch, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElAlert, ElButton, ElForm, ElFormItem, ElInput, ElOption, ElSelect, ElTag } from 'element-plus'
import { AdminCourses } from '@/services/admin-courses'
import { adminResourceId } from '@/services/admin-course-navigation'
import { categories, difficultyNames } from '@/types/resources'
import { controlledTags, statusNames } from '@/types/admin'
const route=useRoute(),router=useRouter(),controller=shallowRef(new AdminCourses())
const state=computed(()=>controller.value.state),ready=ref(false)
const creating=computed(()=>route.name==='admin-course-create')
let active=true
onUnmounted(()=>{active=false})
async function load(){
  const owner=new AdminCourses();controller.value=owner;ready.value=false
  if(creating.value){owner.addCourse();ready.value=true;return}
  const id=adminResourceId(route.params.id)
  if(!id){owner.state.error='课程编号无效';return}
  await owner.editCourse(id)
  if(active && owner===controller.value){ready.value=owner.state.courseEditor;if(ready.value && route.query.saved==='1')owner.state.notice='课程已保存'}
}
async function save(){
  if(!ready.value)return
  const owner=controller.value,result=await owner.saveCourse()
  if(result && active && owner===controller.value && creating.value)await router.replace({name:'admin-course-edit',params:{id:result.id},query:{saved:'1'}})
}
async function status(){const owner=controller.value;if(ready.value && owner.state.editingResource)await owner.status(owner.state.editingResource)}
watch(()=>[route.name,route.params.id],load,{immediate:true})
</script>
<template>
  <section class="admin-editor-page"><ElButton :disabled="state.busy" @click="router.push({name:'admin-courses'})">返回课程列表</ElButton>
    <header class="page-header"><p>课程管理 / {{creating?'创建课程':'编辑课程'}}</p><h1>{{creating?'创建课程':'编辑课程信息'}}</h1></header>
    <ElAlert v-if="state.error" :title="state.error" type="error" :closable="false" role="alert" />
    <ElAlert v-if="state.notice" :title="state.notice" type="success" :closable="false" role="status" />
    <p v-if="state.busy && !ready" role="status">正在读取课程信息…</p><ElButton v-if="!ready && !state.busy" @click="load">重新加载课程</ElButton>
    <article v-if="ready" class="panel">
      <div v-if="state.editingResource" class="course-buttons"><ElTag>{{state.editingResource.status==='offline'?'已隐藏':statusNames[state.editingResource.status]}}</ElTag><ElButton :disabled="state.busy" @click="status">{{state.editingResource.status==='published'?'隐藏课程':'发布课程'}}</ElButton></div>
      <ElForm label-position="top" :disabled="state.busy"><ElFormItem label="课程标题"><ElInput v-model="state.courseForm.title" aria-label="课程标题" maxlength="200" /></ElFormItem><ElFormItem label="课程简介"><ElInput v-model="state.courseForm.summary" aria-label="课程简介" type="textarea" maxlength="1000" /></ElFormItem>
        <div class="form-grid"><ElFormItem label="分类"><ElSelect v-model="state.courseForm.category_code" aria-label="课程分类"><ElOption v-for="[code,name] in categories" :key="code" :value="code" :label="name" /></ElSelect></ElFormItem><ElFormItem label="难度"><ElSelect v-model="state.courseForm.difficulty" aria-label="课程难度"><ElOption v-for="level in [1,2,3]" :key="level" :value="level" :label="difficultyNames[level]" /></ElSelect></ElFormItem></div>
        <ElFormItem label="课程受控标签（发布必填）"><ElSelect v-model="state.courseForm.tags" aria-label="课程标签" multiple><ElOption v-for="tag in controlledTags" :key="tag" :value="tag" :label="tag" /></ElSelect></ElFormItem>
        <ElFormItem label="课程介绍（发布时介绍或外链至少一项）"><ElInput v-model="state.courseForm.content" aria-label="课程介绍" type="textarea" :rows="5" maxlength="100000" /></ElFormItem><ElFormItem label="公开HTTP/HTTPS课程外链（选填）"><ElInput v-model="state.courseForm.content_url" aria-label="课程外链" maxlength="1000" /></ElFormItem>
        <ElFormItem label="来源名称"><ElInput v-model="state.courseForm.source_name" maxlength="255" /></ElFormItem><ElFormItem label="许可说明"><ElInput v-model="state.courseForm.license_note" maxlength="500" /></ElFormItem>
      </ElForm><div class="course-buttons"><ElButton :disabled="state.busy" @click="router.push({name:'admin-courses'})">返回课程列表</ElButton><ElButton type="primary" :loading="state.busy" :disabled="state.loading || !ready" @click="save">保存课程</ElButton></div>

    </article>
  </section>
</template>
<style scoped>
.admin-editor-page{max-width:900px;margin:auto}.page-header{margin:20px 0}.page-header h1{font-size:26px;margin-bottom:8px}.page-header p{color:#64748b;line-height:1.7}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}.course-buttons{display:flex;gap:12px;flex-wrap:wrap;margin-top:24px;padding-top:20px;border-top:1px solid #e5e7eb}.course-buttons .el-button{margin-left:0}@media(max-width:700px){.form-grid{grid-template-columns:1fr}.page-header h1{font-size:22px}.panel{padding:18px}.course-buttons .el-button{flex:1}}
</style>
