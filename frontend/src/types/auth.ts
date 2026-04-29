// User and Authentication types
export interface User {
  id: number
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
}

export interface RegisterData {
  email: string
  password: string
  password_confirm: string
  first_name?: string
  last_name?: string
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
