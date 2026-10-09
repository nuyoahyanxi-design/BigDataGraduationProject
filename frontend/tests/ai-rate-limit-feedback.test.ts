import {afterEach,expect,it} from 'vitest'
import {AxiosError} from 'axios'
import {ApiError,http,request} from '../src/api/http'
import {aiRequestError,AI_PROVIDER_BUSY_MESSAGE} from '../src/services/ai-feedback'
import {aiStatus,type AIRecord} from '../src/types/assistant'

const original=http.defaults.adapter
afterEach(()=>{http.defaults.adapter=original})
it.each([
  ['user_daily','额度已用完'],['global_daily','平台本日'],['concurrency','正在处理'],[undefined,'暂时受限'],
])('内部429来源%s显示友好说明，不展示HTTP状态', (source,message)=>{
  const text=aiRequestError(new ApiError('服务请求失败（HTTP 429）',429,source),'失败')
  expect(text).toContain(message);expect(text).not.toContain('HTTP')
})
it('供应商限流保持独立提示和历史错误标记',()=>{
  expect(aiRequestError(new ApiError('HTTP 502',502,'provider_rate_limit'),'失败')).toBe(AI_PROVIDER_BUSY_MESSAGE)
  expect(aiStatus({error_code:'provider_rate_limit',status:'failed'} as AIRecord)).toBe(AI_PROVIDER_BUSY_MESSAGE)
})
it.each(['user_daily','untrusted-header-value'])('Axios只传递白名单来源%s且不自动重试',async source=>{
  let calls=0
  http.defaults.adapter=async config=>{calls++;throw new AxiosError('request failed','ERR_BAD_RESPONSE',config,undefined,
    {config,status:429,statusText:'Too Many Requests',headers:{'x-ai-limit-source':source},data:{detail:'Daily AI request limit reached'}})}
  try{await request({method:'POST',url:'/ai/questions',skipAuth:true});throw new Error('Expected rejection')}
  catch(problem){expect(problem).toBeInstanceOf(ApiError);expect((problem as ApiError).aiLimitSource).toBe(source==='user_daily'?source:undefined)}
  expect(calls).toBe(1)
})
