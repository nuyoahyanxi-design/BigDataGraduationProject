// Isolated mock harness, not referenced by the production entry point.
import { createApp } from 'vue'
import { createRouter,createMemoryHistory } from 'vue-router'
import App from '../src/App.vue'
import AdminView from '../src/views/AdminView.vue'
import ForbiddenView from '../src/views/ForbiddenView.vue'
import LoginView from '../src/views/LoginView.vue'
import HomeView from '../src/views/HomeView.vue'
import { pinia } from '../src/stores'
import { useAuthStore } from '../src/stores/auth'
import { createAuthGuard } from '../src/router/auth-guard'
import { http } from '../src/api/http'
import type { ResourceDetail } from '../src/types/resources'
import 'element-plus/dist/index.css'
import '../src/styles/base.css'
const params=new URLSearchParams(location.search), role=params.has('learner')?'learner':'admin'
const auth=useAuthStore(pinia)
if(!params.has('anonymous')){
  auth.token='invalid-component-test-placeholder';auth.expiresAt=Date.now()+3600000;auth.restored=true
  auth.user={id:1,username:'component_test_'+role,nickname:null,role,status:'active',interest_tags:[],created_at:'',updated_at:''}
} else { auth.clear() }
const time='2026-10-05T00:00:00Z'
let resources:ResourceDetail[]=params.has('empty')?[]:[{id:100,title:'Spark模拟资源',summary:'管理员组件验证简介',resource_type:'document',category_code:'data-engineering',tags:['spark'],difficulty:1,content:'模拟正文',content_url:null,source_name:'组件测试',license_note:null,status:'draft',version_no:1,created_by:1,published_at:null,created_at:time,updated_at:time}]
http.defaults.adapter=async config=>{
  let data:unknown
  const payload=typeof config.data==='string'?JSON.parse(config.data):config.data
  if(config.url==='/admin/users')data={items:params.has('empty')?[]:[{id:1,username:'component_test_admin',role:'admin',status:'active',created_at:time},{id:2,username:'component_test_learner',role:'learner',status:'active',created_at:time}],total:params.has('empty')?0:2,page:1,page_size:20}
  else if(config.url==='/admin/batches')data={scope:'模拟最近发布记录，非真实执行历史',items:params.has('empty')?[]:[{stage:'推荐计算',batch_id:'component_recommendation_batch',status:'completed',generated_at:time,as_of_utc:time,data_count:30,count_label:'推荐行数',source:'component-fixture',message:null}]}
  else if(config.url==='/resources' && config.method==='post'){
    const item={...resources[0],...payload,id:101,status:'draft',version_no:1,created_by:1,published_at:null,created_at:time,updated_at:time} as ResourceDetail;resources.unshift(item);data=item
  }else if(config.url==='/resources'){
    const q=config.params?.q||'',status=config.params?.status||'all'
    const items=resources.filter(r=>r.title.includes(q)&&(status==='all'||r.status===status));data={items,total:items.length,page:1,page_size:10}
  }else{
    const match=config.url?.match(/^\/resources\/(\d+)(\/status)?$/);if(!match)throw new Error('Unexpected harness request')
    const item=resources.find(r=>r.id===Number(match[1]));if(!item)throw new Error('Fixture not found')
    if(config.method==='put'){Object.assign(item,payload);item.version_no++}
    else if(config.method==='patch'){item.status=payload.status;item.version_no++}
    data={...item}
  }
  return {config,data,status:200,statusText:'OK',headers:{}}
}
const router=createRouter({history:createMemoryHistory(),routes:[
  {path:'/',name:'home',component:HomeView,meta:{requiresAuth:true}},
  {path:'/login',name:'login',component:LoginView},
  {path:'/admin',name:'admin',component:AdminView,meta:{requiresAuth:true,roles:['admin'],forbiddenRoute:'forbidden'}},
  {path:'/403',name:'forbidden',component:ForbiddenView,meta:{requiresAuth:true}},
  {path:'/resources',name:'resources',component:HomeView},{path:'/recommendations',name:'recommendations',component:HomeView},{path:'/dashboard',name:'dashboard',component:HomeView},
]})
router.beforeEach(createAuthGuard(auth));await router.push('/admin')
createApp(App).use(pinia).use(router).mount('#app')
