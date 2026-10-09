<script setup lang="ts">
import { ElResult, ElButton } from 'element-plus'
</script>
<template><ElResult icon="warning" title="403 · 禁止访问" sub-title="管理员后台仅管理员角色可访问"><template #extra><ElButton @click="$router.replace('/')">返回首页</ElButton></template></ElResult></template>
