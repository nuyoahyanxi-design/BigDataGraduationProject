<script setup lang="ts">
import type { Chapter } from '@/types/courses'
defineProps<{ chapters: Chapter[]; selected: number | undefined; disabled: boolean; courseTitle?: string }>()
defineEmits<{ select: [chapter: Chapter] }>()
</script>
<template>
  <nav class="chapter-navigation" aria-label="课程章节目录">
    <p class="catalog-label">课程目录</p><h2 v-if="courseTitle" class="catalog-title">{{courseTitle}}</h2>
    <h3>章节列表</h3><button v-for="chapter in chapters" :key="chapter.id"
    :disabled="disabled" :aria-current="chapter.id === selected ? 'step' : undefined" @click="$emit('select',chapter)">
    <span class="chapter-title">{{ chapter.completed ? '✓' : '○' }} {{ chapter.position }}. {{ chapter.title }}</span>
  </button></nav>
</template>
<style scoped>
.chapter-navigation{display:block;width:100%;min-width:0;box-sizing:border-box;gap:0}
.catalog-label{margin:0 0 8px;color:#7c8a9d;font-size:12px;letter-spacing:2px}
.catalog-title{font-size:19px;line-height:1.5;margin:0 0 24px;color:#172b4d;overflow-wrap:break-word}
h3{font-size:13px;font-weight:500;color:#66778b;margin:0 0 12px}
button{display:block;width:100%;min-width:0;box-sizing:border-box;text-align:left;border:1px solid transparent;background:transparent;padding:12px;margin:6px 0;border-radius:8px;cursor:pointer;font:inherit;font-size:14px;line-height:1.65;color:#45546b;white-space:normal;word-break:normal;overflow-wrap:break-word}
.chapter-title{display:block;min-width:0;white-space:normal;word-break:normal}
button:hover:not(:disabled){background:#f0f5fb;color:#246bd3}
button[aria-current]{border-color:#d4e4ff;background:#eaf2ff;color:#246bd3;font-weight:600}
button:focus-visible{outline:2px solid #409eff;outline-offset:2px}
button:disabled{cursor:wait;opacity:.65}
</style>
