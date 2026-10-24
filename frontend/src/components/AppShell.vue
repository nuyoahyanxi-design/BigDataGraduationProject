<script setup lang="ts">
import { useApplicationStore } from '@/stores/application'
import { useAuthStore } from '@/stores/auth'
import { ref, watch } from 'vue'
import { getAICapabilities } from '@/api/assistant'
import { useRoute } from 'vue-router'
const route = useRoute()
const application = useApplicationStore()
const auth = useAuthStore()
const aiEnabled = ref(false)
watch(() => auth.token, async (token) => {
  aiEnabled.value = false
  if (!token) return
  try { const value = await getAICapabilities(); if (auth.token === token) aiEnabled.value = value.enabled }
  catch { /* Optional AI must never block the navigation shell. */ }
}, { immediate: true })
</script>

<template>
  <div class="app-shell" :class="{ 'course-theme': route.name === 'course-learning' }">
    <header class="header">
      <span class="brand">{{ application.title }}</span>
      <nav aria-label="主导航">
        <RouterLink to="/">首页</RouterLink>
        <RouterLink to="/resources">学习资源</RouterLink>
        <RouterLink to="/recommendations">个性化推荐</RouterLink>
        <RouterLink v-if="aiEnabled" to="/assistant">AI学习助手</RouterLink>
        <RouterLink v-if="auth.role === 'admin'" to="/dashboard">数据看板</RouterLink>
        <RouterLink v-if="auth.role === 'admin'" to="/admin">管理员后台</RouterLink><RouterLink v-if="auth.role === 'admin'" to="/admin/courses">课程管理</RouterLink>
        <RouterLink to="/login">登录</RouterLink>
      </nav>
    </header>
    <main class="main" :class="{ 'main--course': route.name === 'course-learning' }"><slot /></main>
    <footer>智能学习平台 · 学习与探索</footer>
  </div>
</template>
<style scoped>
.main--course{width:min(1600px,calc(100% - 48px));margin:32px auto}
@media(max-width:600px){.main--course{width:calc(100% - 24px);margin:24px auto}}
.course-theme{background:#faf9f5;min-height:100vh;color:#3d3d3a;--el-color-primary:#a9583e;--el-color-primary-light-3:#c58a74;--el-color-primary-light-5:#d8ac9c;--el-color-primary-light-7:#ead2c8;--el-color-primary-light-8:#f1e1da;--el-color-primary-light-9:#faf2ee;--el-color-primary-dark-2:#88452f;--el-border-color:#e6dfd8;--el-text-color-primary:#141413;--el-text-color-regular:#3d3d3a}
.course-theme>.header{background:#faf9f5;border-bottom-color:#e6dfd8;padding:20px 28px;gap:24px}
.course-theme .brand{color:#292720;letter-spacing:.02em}
.course-theme nav a{color:#6c6a64}.course-theme nav a:hover,.course-theme nav a.router-link-active{color:#a9583e}
.course-theme>footer{color:#77736b;border-top:1px solid #e6dfd8;padding:24px}
@media(max-width:900px){.course-theme>.header{flex-wrap:wrap}.course-theme nav{flex-wrap:wrap;gap:14px}}
</style>

