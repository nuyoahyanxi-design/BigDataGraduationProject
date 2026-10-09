<script setup lang="ts">
import { computed } from 'vue'
import { ElButton } from 'element-plus'
const props = defineProps<{ text: string; errorCode: string | null; expanded: boolean }>()
const emit = defineEmits<{ 'update:expanded': [value: boolean] }>()
const collapsible = computed(() => props.text.length > 1200)
const visibleText = computed(() => collapsible.value && !props.expanded ? props.text.slice(0, 1200) + '…' : props.text)
</script>

<template>
  <div>
    <p v-if="errorCode === 'answer_truncated' && !expanded">回答内容较长，点击展开完整内容</p>
    <p v-if="errorCode === 'answer_truncated'">展开仅显示已保存内容。此记录带有截断标记，新回答最多保留30,000字符；未保存或未生成的部分无法恢复。</p>
    <p v-if="errorCode === 'provider_output_limited'">模型达到输出上限，已显示实际返回内容，回答可能尚未完成。</p>
    <div class="plain-answer">{{ visibleText }}</div>
    <el-button v-if="collapsible || errorCode === 'answer_truncated'" :aria-expanded="expanded" @click="emit('update:expanded', !expanded)">
      {{ expanded ? '收起' : '展开' }}
    </el-button>
  </div>
</template>

<style scoped>
.plain-answer { white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.7; }
</style>
