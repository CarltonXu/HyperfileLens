// User and Authentication types
export interface User {
  id: string
  email: string
  username?: string
  first_name?: string
  last_name?: string
  full_name?: string
  role?: Role
  tenant_role?: 'admin' | 'member'
  tenant?: string
  tenant_name?: string
  phone?: string
  avatar?: string
  preferences?: Record<string, any>
  date_joined: string
  last_login_at?: string
  is_active: boolean
  is_superuser: boolean
  mfa_enabled?: boolean
  mfa_method?: 'email' | 'totp'
}

export interface Role {
  id: number
  name: string
  code: string
  description: string
  permissions: Record<string, boolean>
}

export interface LoginCredentials {
  email: string
  password: string
  captcha_key?: string
  captcha_code?: string
}

export interface LoginResponse {
  user?: User
  token?: string
  mfa_required?: boolean
  user_id?: string
  mfa_method?: 'email' | 'totp'
  login_token?: string
}

export interface RegisterData {
  email: string
  password: string
  password_confirm: string
  first_name?: string
  last_name?: string
  captcha_key?: string
  captcha_code?: string
}

export interface APIToken {
  id: number
  name: string
  prefix: string
  scopes: string[]
  rate_limit: number
  is_active: boolean
  created_at: string
  last_used_at?: string
  expires_at?: string
}
