import { reactive } from 'vue'
import { ApiError } from '@/api/http'
import { getResource, getLearningState, sendLearningEvent } from '@/api/resources'
import type { ResourceDetail, ProgressStatus, LearningAction, EventPayload, EventReceipt } from '@/types/resources'

export function resourceError(error: unknown) {
  if (error instanceof ApiError && error.status === 404) return '资源不存在或已下架'
  if (error instanceof ApiError && error.status === 409) return '操作与当前状态冲突，请重新查询状态'
  return error instanceof Error ? error.message : '请求失败，请稍后重试'
}
export class ResourceLearning {
  private viewed = false
  readonly sessionId = crypto.randomUUID()
  readonly state = reactive({
    resource: null as ResourceDetail | null, progress: 'not_started' as ProgressStatus, favorite: false,
    loading: false, busy: false, stateReady: false, error: '', stateError: '', actionError: '', viewError: '', notice: '',
    pending: null as { action: LearningAction; payload: EventPayload } | null,
    viewPending: null as EventPayload | null, lastReceipt: null as EventReceipt | null,
  })
  constructor(readonly id: number) {}
  async load() {
    this.state.loading = true; this.state.error = ''
    try {
      this.state.resource = await getResource(this.id)
      try { await this.refreshState() } catch { /* resource can still be read */ }
    } catch (error) { this.state.error = resourceError(error) }
    finally { this.state.loading = false }
  }
  async refreshState() {
    this.state.stateReady = false; this.state.stateError = ''
    try {
      const result = await getLearningState(this.id)
      this.state.progress = result.progress; this.state.favorite = result.favorite; this.state.stateReady = true
    } catch (error) { this.state.stateError = '无法读取当前学习或收藏状态，请重新查询'; throw error }
  }
  private payload(view = false): EventPayload {
    return { event_uuid: crypto.randomUUID(), session_id: this.sessionId, ...(view ? { client_occurred_at: new Date().toISOString() } : {}) }
  }
  async recordView() {
    if (this.viewed) return
    if (this.state.viewPending === null) this.state.viewPending = this.payload(true)
    this.state.viewError = ''
    try {
      await sendLearningEvent(this.id, 'view', this.state.viewPending)
      this.viewed = true
      this.state.viewPending = null
    } catch (error) { this.state.viewError = '浏览记录未确认：' + resourceError(error) }
  }
  async perform(action: Exclude<LearningAction, 'view'>) {
    if (this.state.busy || !this.state.stateReady) return
    if (this.state.pending && this.state.pending.action !== action) return
    if (!this.state.pending) {
      if (action === 'start' && this.state.progress !== 'not_started') return
      if (action === 'complete' && this.state.progress !== 'in_progress') return
      if (action === 'favorite' && this.state.favorite || action === 'unfavorite' && !this.state.favorite) return
      this.state.pending = { action, payload: this.payload() }
    }
    this.state.busy = true; this.state.actionError = ''; this.state.notice = ''
    try {
      const result = await sendLearningEvent(this.id, action, this.state.pending.payload)
      this.state.lastReceipt = result
      this.state.pending = null
      this.state.notice = result.is_effective ? '操作成功，行为已记录' : '当前状态未变化，操作回执已记录'
      try { await this.refreshState() } catch { /* event succeeded; state refresh is a separate failure */ }
    } catch (error) {
      this.state.actionError = resourceError(error)
      if (error instanceof ApiError && error.status && error.status < 500) {
        this.state.pending = null
        if (error.status === 404 || error.status === 409) {
          try { await this.refreshState() } catch { /* disable actions until state is known */ }
        }
      }
      else this.state.actionError += '；提交结果尚未确认，请重试原操作'
    } finally { this.state.busy = false }
  }
}
