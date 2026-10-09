<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElAlert, ElButton, ElForm, ElFormItem, ElInput, type FormInstance, type FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { ApiError } from '@/api/http'
const auth = useAuthStore()
const router = useRouter()
const form = ref<FormInstance>()
const values = reactive({ username: '', password: '' })
const submitting = ref(false)
const errorMessage = ref('')
const rules: FormRules = {
  username: [{ validator: (_rule, value, callback) =>
    /^[a-zA-Z0-9_]{3,50}$/.test(String(value).trim())
      ? callback() : callback(new Error('请输入 3–50 位字母、数字或下划线')), trigger: 'blur' }],
  password: [{ min: 8, max: 128, required: true, message: '密码长度应为 8–128 位', trigger: 'blur' }],
}
async function submit() {
  if (submitting.value || !form.value) return
  if (!await form.value.validate().catch(() => false)) return
  submitting.value = true; errorMessage.value = ''
  try {
    await auth.signIn({ username: values.username.trim().toLowerCase(), password: values.password })
    values.password = ''
    await router.replace({ name: 'home' })
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : '登录失败，请稍后重试'
    values.password = ''
  } finally { submitting.value = false }
}
async function retry() {
  if (submitting.value) return
  submitting.value = true
  try { await auth.restore(); if (auth.authenticated) await router.replace({ name: 'home' }) }
  catch { errorMessage.value = '服务暂时不可用，请稍后重试' }
  finally { submitting.value = false }
}
</script>
<template>
  <section class="panel login-panel">
    <h1>登录</h1><p>登录后查看个人账户信息。</p>
    <ElAlert v-if="errorMessage || auth.notice" :title="errorMessage || auth.notice" type="error" :closable="false" show-icon role="alert" />
    <ElForm ref="form" :model="values" :rules="rules" label-position="top" @submit.prevent="submit">
      <ElFormItem label="用户名" prop="username">
        <ElInput v-model="values.username" aria-label="用户名" autocomplete="username" maxlength="50" :disabled="submitting" />
      </ElFormItem>
      <ElFormItem label="密码" prop="password">
        <ElInput v-model="values.password" aria-label="密码" type="password" show-password autocomplete="current-password" maxlength="128" :disabled="submitting" />
      </ElFormItem>
      <ElButton type="primary" native-type="submit" :loading="submitting">登录</ElButton>
      <ElButton v-if="auth.token" :disabled="submitting" @click="retry">重试恢复会话</ElButton>
    </ElForm>
  </section>
</template>
