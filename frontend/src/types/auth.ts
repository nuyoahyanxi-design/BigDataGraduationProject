export interface User {
  id: number
  username: string
  nickname: string | null
  role: 'learner' | 'admin'
  status: 'active' | 'disabled' | 'deleted'
  interest_tags: string[]
  created_at: string
  updated_at: string
}
export interface Credentials { username: string; password: string; captcha_id?: string; captcha_answer?: string; remember_me?: boolean }
export interface TokenResponse { access_token: string; token_type: 'bearer'; expires_in: number }

export interface Captcha { captcha_id: string; image: string; expires_in: number }
export interface RecoveryResult { recovery_code: string; message: string }
