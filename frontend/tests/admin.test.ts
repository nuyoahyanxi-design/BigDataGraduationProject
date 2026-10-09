import { afterEach, expect, it, vi } from 'vitest'
import { http } from '../src/api/http'
import { listAdminUsers,getAdminBatches,listAdminResources,createResource,updateResource,changeResourceStatus } from '../src/api/admin'
import { createAuthGuard } from '../src/router/auth-guard'
import { newResource,resourcePayload,validateResource,utcTime } from '../src/types/admin'
import { memoryStorage,newSession } from './helpers'
const adapter=http.defaults.adapter
afterEach(()=>{http.defaults.adapter=adapter;vi.unstubAllGlobals()})
for(const role of ['anonymous','learner','admin'] as const) it(`管理员入口权限 ${role}`,async()=>{
  memoryStorage();const auth=newSession()
  if(role!=='anonymous'){auth.token='invalid-unit-test-placeholder';auth.expiresAt=Date.now()+60000;auth.restored=true;auth.user={id:1,username:'fixture',nickname:null,role,status:'active',interest_tags:[],created_at:'',updated_at:''}}
  const result=await createAuthGuard(auth)({name:'admin',meta:{requiresAuth:true,roles:['admin'],forbiddenRoute:'forbidden'}})
  expect(result).toEqual(role==='anonymous'?{name:'login'}:role==='learner'?{name:'forbidden'}:true)
})
it('只读接口与资源接口参数复用',async()=>{
  const requests:unknown[]=[]
  http.defaults.adapter=async config=>{requests.push({url:config.url,method:config.method,params:config.params,data:config.data?JSON.parse(config.data):undefined});return {config,status:200,statusText:'OK',headers:{},data:{}}}
  await listAdminUsers(2);await getAdminBatches();await listAdminResources(3,' Spark ','offline')
  const value=newResource();value.title='Title';value.summary='Summary'
  await createResource(value);await updateResource(42,value);await changeResourceStatus(42,'published')
  expect(requests[0]).toMatchObject({url:'/admin/users',params:{page:2,page_size:20}})
  expect(requests[1]).toMatchObject({url:'/admin/batches',method:'get'})
  expect(requests[2]).toMatchObject({url:'/resources',params:{page:3,page_size:10,status:'offline',q:'Spark'}})
  expect(requests[3]).toMatchObject({url:'/resources',method:'post'})
  expect(requests[4]).toMatchObject({url:'/resources/42',method:'put'})
  expect(requests[5]).toMatchObject({url:'/resources/42/status',method:'patch',data:{status:'published'}})
})
it('表单规范化不会提交状态作者版本，空字段转null',()=>{
  const value={...newResource(),title:' title ',summary:' summary ',content:' ',status:'published',created_by:1}
  const result=resourcePayload(value)
  expect(result.title).toBe('title');expect(result.content).toBeNull();expect(result).not.toHaveProperty('status');expect(result).not.toHaveProperty('created_by')
})
it('空标题和不受控标签拒绝',()=>{
  const value=newResource();expect(validateResource(value)).toContain('标题')
  value.title='title';value.summary='summary';value.tags=['spark','spark'];expect(validateResource(value)).toContain('标签')
  value.tags=['unsafe'];expect(validateResource(value)).toContain('标签')
  value.tags=['spark'];expect(validateResource(value)).toBe('')
})
it('历史时间按UTC解释，缺失时间不补造',()=>{
  expect(utcTime('2026-10-04 15:23:33.482')).toContain('15:23:33 UTC');expect(utcTime(null)).toBe('未记录')
})
