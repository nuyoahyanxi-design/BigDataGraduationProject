import { reactive } from 'vue'
import { ApiError } from '@/api/http'
import { listAdminCourses, createChapter, updateChapter, deleteChapter } from '@/api/admin-courses'
import { createResource, updateResource, changeResourceStatus } from '@/api/admin'
import { getResource } from '@/api/resources'
import { getCourse } from '@/api/courses'
import { newResource, resourcePayload, validateResource, type ResourceWrite } from '@/types/admin'
import { chapterForm, chapterPayload, validateChapter } from '@/types/admin-courses'
import type { Chapter, Course } from '@/types/courses'
import type { AdminCourseSummary } from '@/types/admin-courses'
import type { Page, ResourceSummary, ResourceDetail } from '@/types/resources'
const failure=(e:unknown)=>e instanceof ApiError && e.status===409
  ? '操作被拒绝：排序可能重复；已有学习记录的课程不能增删或重排章节。请检查后重试。'
  : e instanceof Error ? e.message : '操作失败，请稍后重试'
export class AdminCourses {
  private generation=0
  readonly state=reactive({list:undefined as Page<AdminCourseSummary>|undefined,page:1,query:'',status:'all',loading:false,busy:false,error:'',notice:'',
    course:undefined as Course|undefined,courseEditor:false,editingCourse:null as number|null,
    editingResource:undefined as ResourceDetail|undefined,
    courseForm:{...newResource(),resource_type:'course'} as ResourceWrite,
    chapterEditor:false,editingChapter:null as number|null,chapterForm:chapterForm(),deleteTarget:null as Chapter|null})
  async load() {
    if(this.state.loading)return
    this.state.loading=true;this.state.error=''
    try{this.state.list=await listAdminCourses(this.state.page,this.state.query,this.state.status)}
    catch(e){this.state.error=failure(e)}finally{this.state.loading=false}
  }
  async select(id:number) {
    const seq=++this.generation
    this.state.error='';this.state.course=undefined;this.state.chapterEditor=false;this.state.deleteTarget=null
    this.state.loading=true
    try{const course=await getCourse(id);if(seq===this.generation)this.state.course=course}
    catch(e){if(seq===this.generation)this.state.error=failure(e)}finally{if(seq===this.generation)this.state.loading=false}
  }
  addCourse(){if(this.state.busy)return;this.state.editingCourse=null;this.state.editingResource=undefined;this.state.courseForm={...newResource(),resource_type:'course'};this.state.courseEditor=true;this.state.error=''}
  async editCourse(id:number){
    if(this.state.busy)return;this.state.busy=true;this.state.error='';this.state.notice=''
    try{const detail=await getResource(id);this.state.editingResource=detail;this.state.courseForm=resourcePayload(detail);this.state.editingCourse=id;this.state.courseEditor=true}
    catch(e){this.state.error=failure(e)}finally{this.state.busy=false}
  }
  async saveCourse(){
    if(this.state.busy)return
    this.state.error=validateResource(this.state.courseForm);if(this.state.error)return
    this.state.busy=true;this.state.notice='' 
    try{
      const data=resourcePayload(this.state.courseForm)
      if(this.state.editingCourse===null)data.resource_type='course'
      const result=this.state.editingCourse===null?await createResource(data):await updateResource(this.state.editingCourse,data)
      this.state.editingResource=result;this.state.courseEditor=false;this.state.notice='课程信息已保存';await this.load()
      if(this.state.course?.resource_id===result.id)await this.select(result.id)
      return result
    }catch(e){this.state.error=failure(e)}finally{this.state.busy=false}
  }
  async status(row:ResourceSummary){
    if(this.state.busy)return;this.state.busy=true;this.state.error='';this.state.notice=''
    try{const result=await changeResourceStatus(row.id,row.status==='published'?'offline':'published');if(this.state.editingResource?.id===row.id)this.state.editingResource=result;this.state.notice=row.status==='published'?'课程已隐藏':'课程已发布';await this.load();if(this.state.course?.resource_id===row.id)await this.select(row.id)}
    catch(e){this.state.error=failure(e)}finally{this.state.busy=false}
  }
  editChapter(chapter?:Chapter){
    if(this.state.busy||!this.state.course)return
    this.state.error='';this.state.editingChapter=chapter?.id??null
    this.state.chapterForm=chapterForm(chapter,Math.max(0,...this.state.course.chapters.map(ch=>ch.position))+1)
    this.state.chapterEditor=true
  }
  async saveChapter(){
    const id=this.state.course?.resource_id
    if(this.state.busy||!id)return
    this.state.error=validateChapter(this.state.chapterForm);if(this.state.error)return
    this.state.busy=true;this.state.notice='' 
    try{
      const payload=chapterPayload(this.state.chapterForm)
      const result=this.state.editingChapter===null?await createChapter(id,payload):await updateChapter(id,this.state.editingChapter,payload)
      this.state.chapterEditor=false;this.state.notice='章节已保存';await this.select(id)
      return result
    }catch(e){this.state.error=failure(e)}finally{this.state.busy=false}
  }
  askDelete(chapter:Chapter){if(!this.state.busy){this.state.deleteTarget=chapter;this.state.error=''}}
  async confirmDelete(){
    const id=this.state.course?.resource_id,target=this.state.deleteTarget
    if(this.state.busy||!id||!target)return
    this.state.busy=true;this.state.error='';this.state.notice=''
    try{await deleteChapter(id,target.id);this.state.deleteTarget=null;this.state.notice='未开始学习的章节已删除';await this.select(id)}
    catch(e){this.state.error=failure(e)}finally{this.state.busy=false}
  }
}

