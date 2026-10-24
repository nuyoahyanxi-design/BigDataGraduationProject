<script setup lang="ts">
import { ref } from 'vue'
import { ElAlert, ElButton, ElCheckbox, ElInput } from 'element-plus'
import { generateRecoveryCode } from '@/api/auth'
import { ApiError } from '@/api/http'
const password=ref(''),code=ref(''),busy=ref(false),error=ref(''),saved=ref(false)
async function generate(){
 if(busy.value||password.value.length<8)return
 busy.value=true;error.value=''
 try{const result=await generateRecoveryCode(password.value);code.value=result.recovery_code;saved.value=false}
 catch(e){error.value=e instanceof ApiError?e.message:'暂时无法生成恢复码'}
 finally{password.value='';busy.value=false}
}
function dismiss(){if(saved.value){code.value='';saved.value=false}}
</script>
<template>
 <details class="account-recovery"><summary>账号安全 · 设置密码恢复码</summary>
  <p>恢复码用于忘记密码时找回账号，仅显示一次。重新生成后，旧码立即失效。</p>
  <ElAlert v-if="error" :title="error" type="error" :closable="false"/>
  <template v-if="code"><code class="recovery-code">{{code}}</code><ElCheckbox v-model="saved">我已安全保存恢复码</ElCheckbox><ElButton :disabled="!saved" @click="dismiss">完成并隐藏</ElButton></template>
  <form v-else @submit.prevent="generate"><label for="recovery-password">验证当前密码</label><ElInput id="recovery-password" v-model="password" type="password" show-password autocomplete="current-password" maxlength="128" aria-label="验证当前密码" :disabled="busy"/><ElButton native-type="submit" :loading="busy" :disabled="password.length<8">生成新的恢复码</ElButton></form>
 </details>
</template>
<style scoped>
.account-recovery{margin-top:28px;border-top:1px solid #e6dfd8;padding-top:20px}.account-recovery summary{cursor:pointer;font-size:13px;color:#a9583e}.account-recovery p{font-size:12px;margin:14px 0}.account-recovery form{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;max-width:540px}.account-recovery label{grid-column:1/-1;font-size:12px;color:#77736b}.recovery-code{display:block;padding:18px;background:#f5f0e8;overflow-wrap:anywhere;user-select:all;margin:18px 0;border-radius:8px}.account-recovery :deep(.el-checkbox){white-space:normal;height:auto}.account-recovery :deep(.el-checkbox__label){white-space:normal}@media(max-width:600px){.account-recovery form{grid-template-columns:1fr}}
</style>
