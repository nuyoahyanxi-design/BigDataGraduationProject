import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { http } from '../src/api/http'
import { SESSION_KEY } from '../src/stores/auth'
import { memoryStorage, newSession } from './helpers'
const original=http.defaults.adapter
const user={id:1,username:'fixture',nickname:null,role:'learner',status:'active',interest_tags:[],created_at:'',updated_at:''}
function storage(){const values=new Map<string,string>();return {getItem:(k:string)=>values.get(k)??null,setItem:(k:string,v:string)=>{values.set(k,v)},removeItem:(k:string)=>{values.delete(k)}}}
beforeEach(()=>{memoryStorage();vi.stubGlobal('localStorage',storage())})
afterEach(()=>{http.defaults.adapter=original;vi.unstubAllGlobals()})
function adapter(){http.defaults.adapter=async config=>({config,status:200,statusText:'OK',headers:{},data:config.url==='/auth/login'?{access_token:'test-only-token',expires_in:604800}:user})}
it('记住我只持久化令牌与截止时间，不保存密码',async()=>{
 adapter();const auth=newSession();await auth.signIn({username:'fixture',password:'fixture-password',remember_me:true})
 const data=JSON.parse(localStorage.getItem(SESSION_KEY)!);expect(Object.keys(data).sort()).toEqual(['expiresAt','token']);expect(sessionStorage.getItem(SESSION_KEY)).toBeNull()
 expect(localStorage.getItem(SESSION_KEY)).not.toContain('fixture-password')
})
it('重开页面可从持久化存储恢复身份',async()=>{
 localStorage.setItem(SESSION_KEY,JSON.stringify({token:'test-only-token',expiresAt:Date.now()+60000}));adapter();const auth=newSession();await auth.restore()
 expect(auth.authenticated).toBe(true);expect(auth.remember).toBe(true)
})
it('未勾选只保存在标签页，清理历史持久会话',async()=>{
 localStorage.setItem(SESSION_KEY,'stale');adapter();const auth=newSession();await auth.signIn({username:'fixture',password:'fixture-password'})
 expect(sessionStorage.getItem(SESSION_KEY)).not.toBeNull();expect(localStorage.getItem(SESSION_KEY)).toBeNull()
})
it('退出清理两种缓存',()=>{
 const data=JSON.stringify({token:'test-only-token',expiresAt:Date.now()+60000});localStorage.setItem(SESSION_KEY,data);sessionStorage.setItem(SESSION_KEY,data)
 newSession().clear();expect(localStorage.getItem(SESSION_KEY)).toBeNull();expect(sessionStorage.getItem(SESSION_KEY)).toBeNull()
})
it('持久化令牌过期时不调用接口且清理缓存',async()=>{
 localStorage.setItem(SESSION_KEY,JSON.stringify({token:'test-only-token',expiresAt:Date.now()-1}));const spy=vi.fn();http.defaults.adapter=spy;const auth=newSession();await auth.restore()
 expect(spy).not.toHaveBeenCalled();expect(localStorage.getItem(SESSION_KEY)).toBeNull()
})
it('持久化受限仍可在内存登录并提示',async()=>{
 vi.stubGlobal('localStorage',{getItem:()=>null,removeItem:()=>{},setItem:()=>{throw Error('blocked')}});adapter();const auth=newSession();await auth.signIn({username:'fixture',password:'fixture-password',remember_me:true})
 expect(auth.authenticated).toBe(true);expect(auth.storageWarning).not.toBe('')
})
