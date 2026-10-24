<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ resourceId: number }>()
const covers: Record<number, string> = {1068:'rdd',1069:'pyspark',1070:'hdfs',1071:'mysql',1072:'machine-learning'}
const source = computed(() => '/images/course-covers/' + (covers[props.resourceId] ?? 'general') + '.svg')
</script>
<template><div class="resource-cover" aria-hidden="true"><img :src="source" alt="" width="640" height="360" loading="lazy" decoding="async" /></div></template>
<style scoped>
.resource-cover{aspect-ratio:16/9;overflow:hidden;background:#f0ece4;border-bottom:1px solid #e6dfd8}.resource-cover img{display:block;width:100%;height:100%;object-fit:cover}
</style>
