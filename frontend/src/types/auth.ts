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
export interface Credentials { username: string; password: string }
export interface TokenResponse { access_token: string; token_type: 'bearer'; expires_in: number }
