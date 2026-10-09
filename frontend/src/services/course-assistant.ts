import { reactive } from 'vue'
import { askAI, getAICapabilities, getAIQuestion } from '@/api/assistant'
import { askCourseAI, getCourseAIQuestion, getCourseAIHistory } from '@/api/course-assistant'
import { validateAIQuestion, type AICapabilities, type AIRecord } from '@/types/assistant'
import type { CourseAIRecord } from '@/types/course-assistant'
import { aiRequestError } from './ai-feedback'
import { ApiError } from '@/api/http'
const failure=(e:unknown,fallback:string)=>e instanceof ApiError && e.status===404
  ? '当前课程不可用或尚未批准资料外发，可切换通用AI继续提问。' : aiRequestError(e,fallback)

export class CourseAssistant {
  private generation=0
  readonly state=reactive({mode:'course' as 'course'|'general',question:'',consent:false,busy:false,loading:false,error:'',
    capabilities:undefined as AICapabilities|undefined,answer:undefined as AIRecord|CourseAIRecord|undefined,
    records:[] as CourseAIRecord[],page:1,total:0,expanded:false})
  constructor(readonly courseId:number, private token:()=>string){}
  dispose(){this.generation++;this.state.answer=undefined;this.state.records=[];this.state.question=''}
  private current(seq:number,token:string){return seq===this.generation && token===this.token()}
  async load(){
    const seq=this.generation,token=this.token();this.state.loading=true
    try{const value=await getAICapabilities();if(this.current(seq,token)){this.state.capabilities=value;if(value.enabled)await this.history()}}
    catch(e){if(this.current(seq,token))this.state.error=aiRequestError(e,'AI暂不可用，课程学习不受影响')}
    finally{if(this.current(seq,token))this.state.loading=false}
  }
  async history(){
    const seq=this.generation,token=this.token()
    try{const value=await getCourseAIHistory(this.courseId,this.state.page);if(this.current(seq,token)){this.state.records=value.items;this.state.total=value.total}}
    catch(e){if(this.current(seq,token)){if(e instanceof ApiError && e.status===404){this.state.records=[];this.state.total=0;if(this.state.mode==='course')this.state.error=failure(e,'课程问答历史暂不可用')}else this.state.error=failure(e,'课程问答历史暂不可用')}}
  }
  mode(value:'course'|'general'){if(this.state.busy)return;this.state.mode=value;this.state.consent=false;this.state.answer=undefined;this.state.expanded=false;this.state.error=''}
  show(record:CourseAIRecord){if(!this.state.busy){this.state.answer=record;this.state.expanded=false}}
  async refresh(){
    const record=this.state.answer;if(!record || this.state.busy)return
    const seq=this.generation,token=this.token()
    try{const value='course_id' in record?await getCourseAIQuestion(this.courseId,record.request_uuid):await getAIQuestion(record.request_uuid)
      if(this.current(seq,token))this.state.answer=value}
    catch(e){if(this.current(seq,token))this.state.error=aiRequestError(e,'状态暂不可用')}
  }
  async send(chapterId?:number){
    if(this.state.busy || !this.state.capabilities?.ready)return
    this.state.error=validateAIQuestion(this.state.question,this.state.consent,'general',undefined);if(this.state.error)return
    const seq=this.generation,token=this.token(),uuid=crypto.randomUUID(),mode=this.state.mode,question=this.state.question.trim()
    this.state.busy=true;this.state.answer=undefined;this.state.expanded=false
    try{
      const value=mode==='course'?await askCourseAI(this.courseId,{request_uuid:uuid,question,chapter_id:chapterId??null,consent_version:this.state.capabilities.consent_version}):
        await askAI({request_uuid:uuid,question,mode:'general',resource_id:null,consent_version:this.state.capabilities.consent_version})
      if(this.current(seq,token))this.state.answer=value
    }catch(e){
      if(this.current(seq,token)){
        this.state.error=mode==='course'?failure(e,'问答暂不可用'):aiRequestError(e,'问答暂不可用')
        try{const value=mode==='course'?await getCourseAIQuestion(this.courseId,uuid):await getAIQuestion(uuid);if(this.current(seq,token))this.state.answer=value}catch{/* Never retry POST automatically. */}
      }
    }finally{if(this.current(seq,token)){this.state.busy=false;await this.history()}}
  }
}
