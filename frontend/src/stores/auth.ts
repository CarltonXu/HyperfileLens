import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User, LoginCredentials, LoginResponse } from '@/types/auth'
import { authApi, mfaApi } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null)
  const token = ref<string | null>(localStorage.getItem('token'))
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const userFullName = computed(() => {
    if (!user.value) return ''
    return [user.value.first_name, user.value.last_name]
      .filter(Boolean)
      .join(' ') || user.value.email
  })
  const userRole = computed(() => user.value?.role?.name || 'User')

  // Actions
  async function login(credentials: LoginCredentials): Promise<LoginResponse> {
    loading.value = true
    error.value = null

    // Clear old token before login to avoid conflicts
    localStorage.removeItem('token')
    token.value = null

    try {
      const response = await authApi.login(
        credentials.email,
        credentials.password,
        credentials.captcha_key,
        credentials.captcha_code
      )

      const data = response.data

      // Check if MFA is required
      if (data.mfa_required) {
        return data
      }

      // Normal login - backend returns flat user data with token
      // Extract token and user data separately
      const { token: authToken, ...userData } = data
      
      if (authToken) {
        token.value = authToken
        user.value = userData as User
        localStorage.setItem('token', authToken)
        // Set flag for welcome toast
        sessionStorage.setItem('showWelcome', 'true')
      }

      return { token: authToken, user: userData, mfa_required: false }
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Login failed'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function verifyMfa(email: string, code: string, loginToken?: string): Promise<LoginResponse> {
    loading.value = true
    error.value = null

    try {
      const response = await mfaApi.verify(email, loginToken || '', code)

      const data = response.data

      // Backend returns flat user data with token
      const { token: authToken, ...userData } = data
      
      if (authToken) {
        token.value = authToken
        user.value = userData as User
        localStorage.setItem('token', authToken)
        // Set flag for welcome toast
        sessionStorage.setItem('showWelcome', 'true')
      }

      return { token: authToken, user: userData, mfa_required: false }
    } catch (err: any) {
      error.value = err.response?.data?.error || 'MFA verification failed'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    try {
      if (token.value) {
        await authApi.logout()
      }
    } catch {
      // Ignore logout errors
    } finally {
      // Clear state
      user.value = null
      token.value = null
      localStorage.removeItem('token')
    }
  }

  async function fetchUser() {
    if (!token.value) return null

    loading.value = true
    error.value = null

    try {
      const response = await authApi.profile()
      user.value = response.data
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Failed to fetch user'
      // Clear invalid token
      if (err.response?.status === 401) {
        token.value = null
        localStorage.removeItem('token')
      }
      throw err
    } finally {
      loading.value = false
    }
  }

  async function register(data: {
    email: string
    password: string
    password_confirm: string
    first_name?: string
    last_name?: string
  }) {
    loading.value = true
    error.value = null

    try {
      const response = await authApi.register({
        email: data.email,
        password: data.password,
        first_name: data.first_name,
        last_name: data.last_name
      })

      const { token: authToken, ...userData } = response.data
      
      token.value = authToken
      user.value = userData as User

      // Store token
      localStorage.setItem('token', authToken)

      return { user: userData as User, token: authToken }
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Registration failed'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateProfile(data: Partial<User>) {
    loading.value = true
    error.value = null

    try {
      const response = await authApi.updateProfile(data as { full_name?: string; phone?: string })
      user.value = response.data
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Failed to update profile'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function changePassword(oldPassword: string, newPassword: string) {
    loading.value = true
    error.value = null

    try {
      await authApi.changePassword({ old_password: oldPassword, new_password: newPassword })
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Failed to change password'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    user,
    token,
    loading,
    error,
    // Getters
    isAuthenticated,
    userFullName,
    userRole,
    // Actions
    login,
    verifyMfa,
    logout,
    fetchUser,
    register,
    updateProfile,
    changePassword
  }
})
