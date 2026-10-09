import { afterEach, expect, it, vi } from 'vitest'
import { http } from '../src/api/http'
import { getDashboard } from '../src/api/dashboard'
import { dashboardCharts } from '../src/services/dashboard-charts'
import { createAuthGuard } from '../src/router/auth-guard'
import { memoryStorage, newSession } from './helpers'
import fixture from './dashboard-fixture.json'
import type { DashboardResponse } from '../src/types/dashboard'
const original = http.defaults.adapter
afterEach(() => { http.defaults.adapter = original; vi.unstubAllGlobals() })
it('看板请求不接受目标用户或前端统计参数', async () => {
  http.defaults.adapter = async (config) => {
    expect(config.url).toBe('/dashboard/overview'); expect(config.params).toBeUndefined()
    return { config, data: fixture, status: 200, statusText: 'OK', headers: {} }
  }
  expect((await getDashboard()).recommendations?.rows).toBe(30)
})
it('匿名看板访问跳转登录', async () => {
  memoryStorage()
  expect(await createAuthGuard(newSession())({ name:'dashboard', meta:{requiresAuth:true,roles:['admin']} })).toEqual({name:'login'})
})
for (const role of ['admin', 'learner'] as const) it(`${role}看板路由权限`, async () => {
  memoryStorage(); const auth = newSession()
  auth.token='invalid-unit-test-placeholder'; auth.expiresAt=Date.now()+60000; auth.restored=true
  auth.user={id:1,username:'fixture',nickname:null,role,status:'active',interest_tags:[],created_at:'',updated_at:''}
  expect(await createAuthGuard(auth)({name:'dashboard',meta:{requiresAuth:true,roles:['admin']}})).toEqual(role==='admin' ? true : {name:'home',query:{notice:'dashboard-forbidden'}})
})
it('图表直接使用服务端已聚合数据', () => {
  const response = fixture as DashboardResponse
  const charts = dashboardCharts(response)
  const trend = charts.trend.series as {data:number[]}[]
  expect(trend).toHaveLength(5)
  expect(trend[0]?.data).toEqual(response.data?.metrics.behavior.daily.map(row=>row.resource_view))
  expect((charts.recommendation.series as {data:number[]}[])[0]?.data).toEqual([15,15])
  expect((charts.completion.series as {data:{value:number}[]}[])[0]?.data.map(row=>row.value)).toEqual([0,1])
})
it('未发布数据不会构造示例统计', () => {
  const charts=dashboardCharts({available:false,data:null,profiles:null,recommendations:null,message:'尚未生成'})
  expect((charts.trend.series as {data:number[]}[]).every(row=>row.data.length===0)).toBe(true)
  expect((charts.recommendation.series as {data:number[]}[])[0]?.data).toEqual([])
})
