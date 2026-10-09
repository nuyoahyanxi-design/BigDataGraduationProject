<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import AiAnswerContent from '@/components/AiAnswerContent.vue'
import { ElTag, ElAlert, ElCard, ElForm, ElFormItem, ElSelect, ElOption, ElInputNumber, ElInput, ElCheckbox, ElButton, ElEmpty, ElPagination } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { askAI, getAICapabilities, getAIHistory, getAIQuestion } from '@/api/assistant'
import { aiStatus, validateAIQuestion, type AICapabilities, type AIRecord } from '@/types/assistant'
import { utcTime } from '@/types/admin'
import { aiRequestError } from '@/services/ai-feedback'

const auth = useAuthStore()
const capabilities = ref<AICapabilities>()
const question = ref(''), mode = ref<'general' | 'resource'>('general'), resourceId = ref<number>()
const consent = ref(false), busy = ref(false), loading = ref(true), error = ref('')
const answer = ref<AIRecord>(), records = ref<AIRecord[]>([]), total = ref(0), page = ref(1)
const answerExpanded = ref(false)
watch(() => answer.value?.request_uuid, () => { answerExpanded.value = false })
let active = true
onUnmounted(() => { active = false; question.value = ''; records.value = []; answer.value = undefined })
const current = (token: string) => active && auth.token === token

async function history() {
  const token = auth.token
  try {
    const data = await getAIHistory(page.value)
    if (current(token)) { records.value = data.items; total.value = data.total }
  } catch (problem) { if (current(token)) error.value = aiRequestError(problem, '历史暂不可用') }
}
onMounted(async () => {
  const token = auth.token
  try {
    const data = await getAICapabilities()
    if (!current(token)) return
    capabilities.value = data
    if (data.enabled) await history()
  } catch { if (current(token)) error.value = 'AI功能暂不可用，现有学习功能不受影响' }
  finally { if (current(token)) loading.value = false }
})

async function send() {
  if (busy.value || !capabilities.value?.ready) return
  error.value = validateAIQuestion(question.value, consent.value, mode.value, resourceId.value)
  if (error.value) return
  const token = auth.token, uuid = crypto.randomUUID()
  busy.value = true
  answer.value = undefined
  try {
    const result = await askAI({ request_uuid: uuid, question: question.value.trim(), mode: mode.value,
      resource_id: mode.value === 'resource' ? resourceId.value! : null, consent_version: capabilities.value.consent_version })
    if (current(token)) answer.value = result
  } catch (problem) {
    if (current(token)) {
      error.value = aiRequestError(problem, '请求失败')
      try { const result = await getAIQuestion(uuid); if (current(token)) answer.value = result } catch { /* no automatic POST retry */ }
    }
  } finally {
    if (current(token)) { busy.value = false; await history() }
  }
}

async function refreshAnswer() {
  if (!answer.value || busy.value) return
  const token = auth.token
  try { const result = await getAIQuestion(answer.value.request_uuid); if (current(token)) answer.value = result }
  catch (problem) { if (current(token)) error.value = aiRequestError(problem, '状态暂不可用') }
}
async function changePage(value: number) { page.value = value; await history() }
</script>

<template>
  <section class="assistant">
    <h1>AI学习助手 <el-tag>P2增强</el-tag></h1>
    <p>单轮知识答疑，不替代资源学习、Spark推荐或教师判断。回答可能有误，请核对原始材料。</p>
    <el-alert v-if="loading" title="正在检查AI功能" :closable="false" />
    <el-alert v-else-if="!capabilities?.enabled" title="AI助手当前关闭，其他学习功能正常使用" type="info" :closable="false" />
    <template v-else>
      <el-alert v-if="!capabilities.ready" title="模型尚未配置，暂不能发送；已有历史仍可查看" type="warning" :closable="false" />
      <el-card>
        <el-form label-position="top" @submit.prevent="send">
          <el-form-item label="问答模式">
            <el-select v-model="mode" aria-label="问答模式" :disabled="busy">
              <el-option label="通用学习问答" value="general" /><el-option label="指定资源答疑（须许可外发）" value="resource" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="mode === 'resource'" label="资源编号">
            <el-input-number v-model="resourceId" :min="1" :max="Number.MAX_SAFE_INTEGER" :disabled="busy" aria-label="资源编号" />
            <p>仅支持已发布且由服务端批准外发的资源片段，不检索全库。</p>
          </el-form-item>
          <el-form-item label="学习问题">
            <el-input v-model="question" type="textarea" :rows="5" :maxlength="2000" show-word-limit :disabled="busy" aria-label="学习问题" />
          </el-form-item>
          <p>{{ capabilities.notice }}</p>
          <el-checkbox v-model="consent" :disabled="busy">我确认将本次问题和所选资料片段发送给外部模型</el-checkbox>
          <p><el-button type="primary" :loading="busy" :disabled="busy || !capabilities.ready" @click="send">发送问题</el-button></p>
        </el-form>
      </el-card>
      <el-card v-if="answer" class="answer">
        <h2>回答</h2><p>{{ aiStatus(answer) }}</p>
        <p>{{ answer.source }} · 模型 {{ answer.model }} · {{ utcTime(answer.finished_at) }}</p>
        <p v-if="answer.resource_id">资源 {{ answer.resource_id }} · 版本 {{ answer.resource_version }}</p>
        <AiAnswerContent v-if="answer.answer" v-model:expanded="answerExpanded" :text="answer.answer" :error-code="answer.error_code" />
        <p v-if="answer.error_code && answer.error_code !== 'provider_timeout'">状态代码：{{ answer.error_code }}</p>
        <el-button v-if="answer.status === 'pending'" @click="refreshAnswer">刷新状态</el-button>
      </el-card>
      <h2>我的历史（最近30天）</h2>
      <el-empty v-if="!records.length" description="暂无问答历史" />
      <el-card v-for="record in records" :key="record.request_uuid" class="history-record">
        <p>{{ record.question }}</p><p>{{ aiStatus(record) }} · {{ utcTime(record.created_at) }}</p>
        <el-button @click="answer = record">查看记录</el-button>
      </el-card>
      <el-pagination v-if="total > 20" :current-page="page" :total="total" :page-size="20" layout="prev, pager, next" @current-change="changePage" />
    </template>
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
  </section>
</template>

<style scoped>
.assistant { max-width: 960px; margin: auto; }
.answer, .history-record { margin: 16px 0; }
.plain-answer { white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.7; }
</style>
