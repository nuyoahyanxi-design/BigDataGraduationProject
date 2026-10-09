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
  <div class="app-shell">
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
    <footer>本科毕业设计 · 学习行为分析与个性化资源推荐</footer>
  </div>
</template>
<style scoped>
.main--course{width:min(1600px,calc(100% - 48px));margin:32px auto}
@media(max-width:600px){.main--course{width:calc(100% - 24px);margin:24px auto}}
</style>

