<script setup lang="ts">
defineProps<{ admin?: boolean }>()
</script>
<template>
 <svg class="workspace-art" viewBox="0 0 320 200" fill="none" aria-hidden="true" focusable="false">
  <circle cx="166" cy="102" r="78" fill="currentColor" opacity=".035"/><ellipse cx="166" cy="102" rx="126" ry="56" transform="rotate(-20 166 102)" stroke="currentColor" opacity=".13" stroke-dasharray="3 7"/>
  <g v-if="admin" stroke="currentColor" stroke-width="1.6"><path d="M160 110v30H85v17m75-17h75v17" opacity=".5"/><path d="M127 62v45c0 18 66 18 66 0V62" fill="#faf9f5"/><ellipse cx="160" cy="62" rx="33" ry="12" fill="#fff"/><path d="M127 84c0 18 66 18 66 0"/><rect x="63" y="157" width="44" height="26" rx="6" fill="#fff"/><rect x="213" y="157" width="44" height="26" rx="6" fill="#fff"/><path d="M74 168h22m128 0h22" opacity=".45"/><rect x="235" y="28" width="51" height="43" rx="8" fill="#fff"/><path d="M246 58V46m10 12V39m10 19V43m10 15V35" opacity=".6"/></g>
  <g v-else stroke="currentColor" stroke-width="1.6"><path d="M110 83q26-13 52 0v74q-26-13-52 0zM162 83q26-13 52 0v74q-26-13-52 0z" fill="#fff"/><path d="M120 102h30m-30 12h30m-30 12h21m31-24h30m-30 12h30m-30 12h21" opacity=".4"/><rect x="42" y="31" width="67" height="46" rx="8" fill="#faf9f5"/><path d="m65 47-9 8 9 8m20-16 9 8-9 8m-7-20-6 24"/><path d="m222 61 25-19 26 27m-26-27-4 52" opacity=".5"/><circle cx="222" cy="61" r="5" fill="#fff"/><circle cx="247" cy="42" r="6" fill="#fff"/><circle cx="273" cy="69" r="5" fill="#fff"/><circle cx="243" cy="94" r="5" fill="#fff"/></g>
  <path d="m65 121 3 8 8 3-8 3-3 8-3-8-8-3 8-3zm194 4 2 5 5 2-5 2-2 5-2-5-5-2 5-2z" fill="currentColor" opacity=".45"/><circle cx="130" cy="30" r="3" fill="currentColor" opacity=".3"/>
 </svg>
</template>
<style scoped>.workspace-art{display:block;width:100%;height:100%;color:#ad7356;pointer-events:none}.workspace-art.admin-art{color:#68827f}</style>
