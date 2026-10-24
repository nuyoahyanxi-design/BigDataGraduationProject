<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElAlert, ElButton, ElCheckbox, ElForm, ElFormItem, ElInput, type FormInstance, type FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { ApiError } from '@/api/http'
import { getCaptcha, registerAccount, resetPassword } from '@/api/auth'
import type { Captcha } from '@/types/auth'
const auth=useAuthStore(),router=useRouter(),form=ref<FormInstance>()
const mode=ref<'login'|'register'|'reset'>('login')
const values=reactive({username:'',password:'',confirmation:'',captcha_answer:'',recovery_code:''})
const remember=ref(false),submitting=ref(false),captchaBusy=ref(false),captcha=ref<Captcha>(),errorMessage=ref(''),recoveryCode=ref(''),saved=ref(false)
const heading=computed(()=>mode.value==='login'?'欢迎回来':mode.value==='register'?'开启学习之旅':'找回你的账号')
const rules:FormRules={
 username:[{validator:(_r,v,cb)=>/^[a-zA-Z0-9_]{3,50}$/.test(String(v).trim())?cb():cb(new Error('请输入 3–50 位字母、数字或下划线')),trigger:'blur'}],
 password:[{min:8,max:128,required:true,message:'密码长度应为 8–128 位',trigger:'blur'}],
 confirmation:[{validator:(_r,v,cb)=>mode.value==='login'||v===values.password?cb():cb(new Error('两次输入的密码不一致')),trigger:'blur'}],
 captcha_answer:[{required:true,min:5,max:5,message:'请输入图片中的 5 位验证码',trigger:'blur'}],
 recovery_code:[{required:true,min:20,max:100,message:'请输入保存的恢复码',trigger:'blur'}],
}
async function refreshCaptcha(){
 if(captchaBusy.value)return
 captchaBusy.value=true;captcha.value=undefined;values.captcha_answer=''
 try{captcha.value=await getCaptcha()}catch(e){errorMessage.value=e instanceof ApiError?e.message:'验证码加载失败，请重试'}finally{captchaBusy.value=false}
}
function changeMode(next:typeof mode.value){
 if(submitting.value||recoveryCode.value)return
 mode.value=next;values.password='';values.confirmation='';values.recovery_code='';errorMessage.value='';form.value?.clearValidate();void refreshCaptcha()
}
async function submit(){
 if(submitting.value||!form.value||!captcha.value)return
 if(!await form.value.validate().catch(()=>false))return
 submitting.value=true;errorMessage.value=''
 const credentials={username:values.username.trim().toLowerCase(),password:values.password,captcha_id:captcha.value.captcha_id,captcha_answer:values.captcha_answer}
 try{
  if(mode.value==='login'){
   await auth.signIn({...credentials,remember_me:remember.value});values.password='';await router.replace({name:'home'})
  }else{
   const result=mode.value==='register'?await registerAccount(credentials):await resetPassword({...credentials,recovery_code:values.recovery_code.trim()})
   recoveryCode.value=result.recovery_code;saved.value=false;values.password='';values.confirmation='';values.recovery_code='';captcha.value=undefined
  }
 }catch(e){errorMessage.value=e instanceof ApiError?e.message:'操作失败，请稍后重试';values.password='';values.confirmation='';await refreshCaptcha()}
 finally{submitting.value=false}
}
function finishRecovery(){if(!saved.value)return;recoveryCode.value='';mode.value='login';errorMessage.value='';void refreshCaptcha()}
async function retry(){
 if(submitting.value)return;submitting.value=true
 try{await auth.restore();if(auth.authenticated)await router.replace({name:'home'})}catch{errorMessage.value='服务暂时不可用，请稍后重试'}finally{submitting.value=false}
}
onMounted(refreshCaptcha)
</script>
<template>
 <section class="auth-page">
  <aside class="auth-story" aria-label="平台介绍">
   <span class="auth-brandmark">LEARN / EXPLORE</span><h2>让每一次学习，<br/>都有清晰的方向。</h2><p>从课程实践到学习回顾，连接知识、行动与新的发现。</p>
   <div class="auth-art" aria-hidden="true"><div class="art-orbit orbit-one"></div><div class="art-orbit orbit-two"></div><div class="art-core">Learn<span>理解 · 实践 · 探索</span></div><span class="art-note note-code">&lt; / &gt;<small>课程实践</small></span><span class="art-note note-data">▥<small>学习画像</small></span><span class="art-note note-ai">✦<small>AI 辅助</small></span></div>
   <div class="auth-story-footer"><span>课程学习</span><span>学习画像</span><span>个性化推荐</span></div>
  </aside>
  <div class="auth-form-area">
   <template v-if="recoveryCode">
    <p class="auth-eyebrow">ACCOUNT RECOVERY</p><h1>请保存你的恢复码</h1><p>这是找回账号的凭证，仅本次显示。请保存在安全的位置，不要分享给他人。</p>
    <ElAlert title="新的恢复码已生效，之前的恢复码不可再使用。" type="warning" :closable="false" />
    <code class="recovery-secret">{{recoveryCode}}</code><ElCheckbox v-model="saved">我已安全保存恢复码</ElCheckbox>
    <ElButton class="auth-submit" type="primary" :disabled="!saved" @click="finishRecovery">返回登录</ElButton>
   </template>
   <template v-else>
    <p class="auth-eyebrow">YOUR LEARNING SPACE</p><h1>{{heading}}</h1><p class="auth-subtitle">{{mode==='login'?'登录后，继续你的学习与探索。':mode==='register'?'创建学习者账号，探索适合自己的课程。':'使用已保存的恢复码，设置新的登录密码。'}}</p>
    <ElAlert v-if="errorMessage || auth.notice" :title="errorMessage || auth.notice" type="error" :closable="false" show-icon role="alert" />
    <ElForm ref="form" :model="values" :rules="rules" label-position="top" @submit.prevent="submit">
     <ElFormItem label="用户名" prop="username" required><ElInput v-model="values.username" aria-label="用户名" autocomplete="username" placeholder="请输入用户名" maxlength="50" :disabled="submitting"><template #prefix><svg class="input-icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/></svg></template></ElInput></ElFormItem>
     <ElFormItem v-if="mode==='reset'" label="恢复码" prop="recovery_code"><ElInput v-model="values.recovery_code" aria-label="恢复码" type="password" show-password autocomplete="off" maxlength="100" placeholder="请输入此前安全保存的恢复码" :disabled="submitting"/></ElFormItem>
     <ElFormItem :label="mode==='reset'?'新密码':'密码'" prop="password" required><ElInput v-model="values.password" aria-label="密码" type="password" show-password :autocomplete="mode==='login'?'current-password':'new-password'" placeholder="请输入 8–128 位密码" maxlength="128" :disabled="submitting"><template #prefix><svg class="input-icon" viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="10" width="16" height="12" rx="3"/><path d="M8 10V6a4 4 0 0 1 8 0v4"/></svg></template></ElInput></ElFormItem>
     <ElFormItem v-if="mode!=='login'" label="确认密码" prop="confirmation" required><ElInput v-model="values.confirmation" aria-label="确认密码" type="password" show-password autocomplete="new-password" maxlength="128" :disabled="submitting" placeholder="再次输入密码"/></ElFormItem>
     <ElFormItem label="验证码" prop="captcha_answer" required><div class="captcha-row"><ElInput v-model="values.captcha_answer" aria-label="验证码" autocomplete="off" maxlength="5" :disabled="submitting || captchaBusy" placeholder="5 位验证码"/><button type="button" class="captcha-image" :disabled="submitting || captchaBusy" aria-label="刷新验证码" @click="refreshCaptcha"><img v-if="captcha" :src="captcha.image" alt="图形验证码" width="180" height="60"/><span v-else>{{captchaBusy?'加载中…':'点击重试'}}</span></button></div><span class="captcha-hint">有效期 2 分钟，点击图片换一张</span></ElFormItem>
     <div v-if="mode==='login'" class="auth-options"><ElCheckbox v-model="remember" :disabled="submitting">记住我 7 天</ElCheckbox><button class="auth-link" type="button" :disabled="submitting" @click="changeMode('reset')">忘记密码？</button></div>
     <p v-if="mode==='login'" class="auth-privacy">公共设备请勿勾选。不保存密码；未勾选时会话有效期为 30 分钟。</p>
     <p v-if="mode==='reset'" class="auth-privacy">尚未设置恢复码的旧账号，请联系系统维护人员核验身份。密码重置后需要重新登录。</p>
     <ElButton class="auth-submit" type="primary" native-type="submit" :loading="submitting" :disabled="!captcha || captchaBusy">{{mode==='login'?'登录':mode==='register'?'创建账号':'重设密码'}}</ElButton>
     <ElButton v-if="auth.token && mode==='login'" :disabled="submitting" @click="retry">重试恢复会话</ElButton>
    </ElForm>
    <p class="auth-switch" v-if="mode==='login'">还没有账号？<button class="auth-link" :disabled="submitting" @click="changeMode('register')">立即注册 <span aria-hidden="true">↗</span></button></p>
    <p class="auth-switch" v-else>已有账号？<button class="auth-link" :disabled="submitting" @click="changeMode('login')">返回登录</button></p>
   </template>
  </div>
 </section>
</template>
<style scoped>
.auth-page{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);border:1px solid #e6dfd8;border-radius:20px;overflow:hidden;background:#fff;box-shadow:0 16px 60px #3d302508;min-width:0}.auth-story{background:#f0e8dd;padding:44px 36px;display:flex;flex-direction:column;min-width:0}.auth-brandmark{font-size:11px;letter-spacing:3px;color:#92715b}.auth-story h2{font-size:30px;line-height:1.65;letter-spacing:-1px;color:#3b332b;margin:36px 0 12px}.auth-story>p{font-size:14px;color:#857567;margin:0;max-width:320px}.auth-story-footer{display:flex;gap:18px;font-size:11px;color:#92715b;margin-top:auto;padding-top:26px;border-top:1px solid #d9cebf}.auth-art{height:240px;position:relative;margin:22px 0 30px;display:grid;place-items:center}.art-orbit{position:absolute;width:230px;height:160px;border:1px solid #c9af9666;border-radius:50%;transform:rotate(-26deg)}.orbit-two{transform:rotate(35deg);width:180px;height:230px}.art-core{z-index:1;background:#faf7f1;border:1px solid #d8c7b4;border-radius:22px;width:124px;height:124px;display:flex;flex-direction:column;justify-content:center;align-items:center;color:#a9583e;font-family:Georgia,serif;font-size:30px;box-shadow:0 10px 30px #82644a0d}.art-core span{font-family:system-ui,sans-serif;font-size:9px;margin-top:12px;color:#92715b}.art-note{position:absolute;z-index:2;background:#fff9;border:1px solid #d8c7b4;border-radius:12px;padding:12px 15px;font-size:20px;color:#a9583e}.art-note small{display:block;font-size:10px;color:#857567;margin-top:5px}.note-code{left:0;top:25px}.note-data{right:0;top:52px}.note-ai{left:45px;bottom:0}.auth-form-area{padding:44px;min-width:0}.auth-eyebrow{font-size:10px;letter-spacing:2px;font-weight:600;color:#a9583e;margin:0 0 12px}.auth-form-area h1{font-size:29px;margin:0 0 10px;color:#292720}.auth-subtitle{font-size:13px;margin:0 0 26px}.auth-form-area .el-form{margin-top:24px}.auth-form-area :deep(.el-input__wrapper){min-height:46px}.input-icon{width:17px;height:17px;fill:none;stroke:#a49585;stroke-width:1.6;margin-right:5px}.captcha-row{display:flex;width:100%;gap:10px}.captcha-row .el-input{min-width:0;flex:1}.captcha-image{padding:0;width:130px;flex-shrink:0;border:1px solid #e6dfd8;border-radius:7px;background:#faf7f1;cursor:pointer;overflow:hidden;height:46px;color:#857567}.captcha-image img{width:100%;height:100%;object-fit:contain}.captcha-hint{font-size:11px;color:#94897e;margin-top:4px}.auth-options{display:flex;justify-content:space-between;align-items:center;gap:12px}.auth-link{color:#a9583e;font:inherit;font-size:13px;border:0;background:none;padding:4px 0;cursor:pointer}.auth-link:disabled{opacity:.5;cursor:wait}.auth-link:focus-visible,.captcha-image:focus-visible{outline:2px solid #a9583e;outline-offset:3px}.auth-privacy{font-size:11px;line-height:1.7;margin:4px 0 22px;color:#94897e}.auth-submit{display:block;width:100%;height:46px;font-size:15px;letter-spacing:2px;border-radius:8px;margin:20px 0 0}.auth-switch{font-size:12px;text-align:center;margin:24px 0 0}.auth-switch button{margin-left:8px}.recovery-secret{display:block;background:#f5f0e8;border:1px solid #e6dfd8;border-radius:8px;padding:18px;margin:24px 0;overflow-wrap:anywhere;user-select:all;font-size:14px;color:#88452f}
@media(max-width:800px){.auth-page{grid-template-columns:minmax(0,1fr);max-width:520px;margin:auto}.auth-story{padding:26px}.auth-story h2{font-size:25px;margin:18px 0 8px}.auth-art,.auth-story-footer{display:none}.auth-story>p{max-width:none}.auth-form-area{padding:30px}}
@media(max-width:420px){.auth-form-area{padding:24px 20px}.auth-story{padding:24px 20px}.auth-form-area h1{font-size:25px}.captcha-image{width:116px}}
</style>
