<script setup lang="ts">
import WorkspaceArt from '@/components/WorkspaceArt.vue'
import RecoverySettings from '@/components/RecoverySettings.vue'
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElAlert, ElButton, ElTag } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
const auth = useAuthStore()
const interestTags = computed(() => Array.isArray(auth.user?.interest_tags) ? auth.user.interest_tags : [])
const router = useRouter()
const route = useRoute()
function logout() { auth.clear(); void router.replace({ name: 'login' }) }
</script>
<template>
  <section class="panel home-account decorated-home" :class="{'decorated-home--admin':auth.role==='admin'}">
    <header class="home-welcome"><div class="home-welcome-copy"><p class="home-eyebrow"><span class="eyebrow-line" aria-hidden="true"></span>{{auth.role==='admin'?'管理工作台':'学习工作台'}}</p><h1>个人账户</h1><p class="home-intro">{{auth.role==='admin'?'查看平台分析与已有课程，清晰掌握数据与内容。':'从一门课程开始，循序学习、回顾知识，并查看与你相关的学习资源。'}}</p></div><WorkspaceArt :admin="auth.role==='admin'" :class="{'admin-art':auth.role==='admin'}"/></header>
    <ElAlert v-if="route.query.notice === 'dashboard-forbidden'" title="数据看板仅管理员可访问" type="warning" :closable="false" />
    <ElAlert v-if="auth.storageWarning" :title="auth.storageWarning" type="warning" :closable="false" />
    <template v-if="auth.user">
      <dl class="user-details">
        <dt>用户名</dt><dd>{{ auth.user.username }}</dd>
        <dt>角色</dt><dd>{{ auth.role === 'admin' ? '管理员' : '学习者' }}</dd>
        <dt>兴趣标签</dt>
        <dd><ElTag v-for="tag in interestTags" :key="tag" class="interest-tag">{{ tag }}</ElTag><span v-if="!interestTags.length">暂无兴趣标签</span></dd>
      </dl>
    </template>
    <div class="home-actions"><ElButton @click="logout">退出登录</ElButton>
    <ElButton type="primary" @click="router.push({ name: 'resources' })">浏览学习资源</ElButton>
    <ElButton @click="router.push({ name: 'recommendations' })">查看个性化推荐</ElButton>
    <ElButton v-if="auth.role === 'admin'" @click="router.push({ name: 'dashboard' })">查看数据看板</ElButton>
    <ElButton v-if="auth.role === 'admin'" @click="router.push({ name: 'admin' })">进入管理员后台</ElButton>
    </div>
    <RecoverySettings />
  </section>
</template>

