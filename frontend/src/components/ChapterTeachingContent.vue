<script setup lang="ts">
import { computed } from 'vue'
import { ElTag } from 'element-plus'
import LearningMarkdown from './LearningMarkdown.vue'
import type { Chapter } from '@/types/courses'
const props = defineProps<{ chapter: Chapter }>()
const objectives = computed(() => Array.isArray(props.chapter.learning_objectives) ? props.chapter.learning_objectives : [])
const knowledge = computed(() => Array.isArray(props.chapter.knowledge_tags) ? props.chapter.knowledge_tags : [])
const exercises = computed(() => Array.isArray(props.chapter.exercises) ? props.chapter.exercises : [])
</script>
<template>
  <div class="chapter-teaching">
    <section aria-label="教学目标"><h3>教学目标</h3>
      <ul v-if="objectives.length"><li v-for="(goal,index) in objectives" :key="index">{{goal}}</li></ul>
      <p v-else>本章节暂未补充教学目标。</p>
    </section>
    <section aria-label="知识点"><h3>知识点</h3>
      <ElTag v-for="tag in knowledge" :key="tag">{{tag}}</ElTag><p v-if="!knowledge.length">暂无知识点标签。</p>
    </section>
    <section aria-label="知识讲解"><h3>知识讲解</h3><LearningMarkdown :content="chapter.content || '本章节暂未提供正文。'" /></section>
    <section aria-label="代码示例"><h3>代码示例</h3>
      <pre v-if="chapter.example_code?.trim()"><code>{{chapter.example_code}}</code></pre>
      <p v-else>本章节暂无独立代码示例。</p>
    </section>
    <section aria-label="章节练习"><h3>章节练习</h3>
      <ol v-if="exercises.length"><li v-for="(exercise,index) in exercises" :key="index">{{exercise}}</li></ol>
      <p v-else>请回顾本章节知识点并整理学习笔记。</p>
      <p class="exercise-note">请在本地环境完成练习；平台不执行代码或自动评分。</p>
    </section>
  </div>
</template>
<style scoped>
.chapter-teaching{max-width:800px;min-width:0;margin:0 auto;line-height:1.9;overflow-wrap:break-word;color:#36465d}
.chapter-teaching section{margin:28px 0;padding-top:8px}
h3{font-size:18px;color:#172b4d;margin:0 0 16px}ul,ol{padding-left:24px;margin:12px 0}li{margin:8px 0}
section[aria-label="教学目标"],section[aria-label="章节练习"]{background:#f7f9fc;border:1px solid #e9edf4;border-radius:10px;padding:20px}
.el-tag{margin:4px 8px 4px 0}
pre{box-sizing:border-box;max-width:100%;white-space:pre;overflow-x:auto;background:#152235;color:#e4edfc;padding:20px;border:1px solid #263953;border-radius:10px;line-height:1.7}
code{font-family:Consolas,"Courier New",monospace;font-size:14px}
.exercise-note{color:#7b889a;font-size:13px}
@media(max-width:600px){section[aria-label="教学目标"],section[aria-label="章节练习"]{padding:16px}pre{padding:16px}}
</style>
