import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User, LoginCredentials } from '@/types/auth'
import api from '@/api'

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
  async function login(credentials: LoginCredentials) {
    loading.value = true
    error.value = null

    try {
      const response = await api.post<{ token: string; [key: string]: any }>(
        '/api/v1/accounts/login/',
        credentials
      )

      // Backend returns user fields + token directly (not nested under 'user')
      const { token: authToken, ...userData } = response.data
      
      token.value = authToken
      user.value = userData as User

      // Store token
      localStorage.setItem('token', authToken)

      return { user: userData as User, token: authToken }
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Login failed'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    try {
      if (token.value) {
        await api.post('/api/v1/accounts/logout/')
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
      const response = await api.get<User>('/api/v1/accounts/profile/')
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
      const response = await api.post<{ token: string; [key: string]: any }>(
        '/api/v1/accounts/register/',
        data
      )

      // Backend returns user fields + token directly (not nested under 'user')
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
      const response = await api.patch<User>(
        '/api/v1/accounts/profile/',
        data
      )
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
      await api.post('/api/v1/accounts/password/', {
        old_password: oldPassword,
        new_password: newPassword,
        new_password_confirm: newPassword
      })
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
    logout,
    fetchUser,
    register,
    updateProfile,
    changePassword
  }
})
