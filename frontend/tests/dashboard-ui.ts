// Isolated harness, excluded from the production entry point.
import { createApp } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import App from '../src/App.vue'
import DashboardView from '../src/views/DashboardView.vue'
import HomeView from '../src/views/HomeView.vue'
import LoginView from '../src/views/LoginView.vue'
import { pinia } from '../src/stores'
import { useAuthStore } from '../src/stores/auth'
import { createAuthGuard } from '../src/router/auth-guard'
import { http } from '../src/api/http'
import fixture from './dashboard-fixture.json'
import 'element-plus/dist/index.css'
import '../src/styles/base.css'
const auth=useAuthStore(pinia)
auth.token='invalid-component-test-placeholder'; auth.expiresAt=Date.now()+3600000; auth.restored=true
auth.user={id:1,username:'component_test_admin',nickname:null,role:'admin',status:'active',interest_tags:[],created_at:'',updated_at:''}
http.defaults.adapter=async(config)=>{
  if(config.url!=='/dashboard/overview') throw new Error('Unexpected harness request')
  return {config,status:200,statusText:'OK',headers:{},data:new URLSearchParams(location.search).has('empty')
    ? {available:false,data:null,profiles:null,recommendations:null,message:'尚无可展示的统计数据'} : fixture}
}
const router=createRouter({history:createMemoryHistory(),routes:[
  {path:'/',name:'home',component:HomeView,meta:{requiresAuth:true}},
  {path:'/login',name:'login',component:LoginView},
  {path:'/dashboard',name:'dashboard',component:DashboardView,meta:{requiresAuth:true,roles:['admin']}},
  {path:'/resources',name:'resources',component:HomeView},
  {path:'/recommendations',name:'recommendations',component:HomeView},
]})
router.beforeEach(createAuthGuard(auth)); await router.push('/dashboard')
createApp(App).use(pinia).use(router).mount('#app')
