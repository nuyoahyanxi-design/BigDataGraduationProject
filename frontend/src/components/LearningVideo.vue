<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { safeVideoAsset } from '@/types/courses'
import { newPlayback, updatePlayback } from '@/services/video-learning'
const props = defineProps<{ url: string | null; cover: string | null; name: string | null; duration: number | null; disabled?: boolean }>()
const emit = defineEmits<{ play: [seconds: number] }>()
const playback = ref(newPlayback())
const mediaDuration = ref<number>()
const source = computed(() => safeVideoAsset(props.url))
const cover = computed(() => safeVideoAsset(props.cover,'images'))
const durationText = computed(() => {
  const duration = props.duration ?? mediaDuration.value
  if (duration == null) return source.value ? '待视频加载' : '暂无'
  const seconds = Math.floor(duration)
  return Math.floor(seconds / 60) + ':' + String(seconds % 60).padStart(2, '0')
})
watch(() => props.url, () => { playback.value=newPlayback(); mediaDuration.value=undefined })
function metadata(event: Event) {
  const duration = (event.target as HTMLVideoElement).duration
  if (Number.isFinite(duration) && duration > 0) mediaDuration.value=duration
}
function position(event: Event) { updatePlayback(playback.value,'timeupdate',(event.target as HTMLVideoElement).currentTime) }
function play(event: Event) {
  updatePlayback(playback.value,'play',(event.target as HTMLVideoElement).currentTime)
  if (!props.disabled) emit('play',playback.value.seconds)
}
</script>
<template>
  <section class="learning-video" aria-label="教学视频"><h3>{{ name || '教学视频' }}</h3>
    <p>视频时长：{{ durationText }}</p>
    <video v-if="source" :key="source" controls preload="metadata" :src="source" :poster="cover"
      @loadedmetadata="metadata" @play="play" @timeupdate="position" @ended="updatePlayback(playback,'ended')" @error="updatePlayback(playback,'error')" />
    <p v-if="!source || playback.failed" role="status">教学视频暂未提供或无法加载，请先阅读下方章节内容。</p>
    <p>当前播放时间：{{ Math.floor(playback.seconds) }} 秒<span v-if="duration"> / 预计 {{ duration }} 秒</span></p>
    <p v-if="playback.ended" role="status">视频播放完成，请阅读章节内容后确认完成本章节。</p>
  </section>
</template>
<style scoped>
.learning-video{min-width:0}h3{font-size:16px;color:#45546b;margin:0 0 14px}
video{display:block;width:100%;height:auto;aspect-ratio:16 / 9;object-fit:contain;background:#111827;border-radius:10px}
p{font-size:13px;color:#7b889a;line-height:1.6;margin:12px 0}
</style>
