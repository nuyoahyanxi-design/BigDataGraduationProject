<script setup lang="ts">
import { computed } from 'vue'
import { learningBlocks } from '@/services/markdown-learning'
const props = defineProps<{ content: string }>()
const blocks = computed(() => learningBlocks(props.content))
</script>
<template>
  <div class="learning-text"><template v-for="(block,index) in blocks" :key="index">
    <h3 v-if="block.kind === 'heading'">{{ block.text }}</h3>
    <pre v-else-if="block.kind === 'code'"><code>{{ block.text }}</code></pre>
    <p v-else>{{ block.text }}</p>
  </template></div>
</template>
<style scoped>
.learning-text{line-height:1.9;overflow-wrap:break-word;color:#36465d;min-width:0}
h3{font-size:17px;color:#243a57;margin:26px 0 12px;padding-bottom:8px;border-bottom:1px solid #edf0f5}
p{margin:14px 0}
pre{box-sizing:border-box;max-width:100%;white-space:pre;overflow-x:auto;background:#152235;color:#e4edfc;padding:20px;border-radius:10px;line-height:1.7}
code{font-family:Consolas,"Courier New",monospace;font-size:14px}
</style>
