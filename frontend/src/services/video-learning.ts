export interface PlaybackState { seconds: number; ended: boolean; failed: boolean }
export const newPlayback = (): PlaybackState => ({ seconds: 0, ended: false, failed: false })
export function updatePlayback(state: PlaybackState, event: 'play' | 'timeupdate' | 'ended' | 'error', seconds = state.seconds) {
  if (Number.isFinite(seconds) && seconds >= 0) state.seconds = seconds
  if (event === 'play') state.ended = false
  if (event === 'ended') state.ended = true
  if (event === 'error') state.failed = true
}
