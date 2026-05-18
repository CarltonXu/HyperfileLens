import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

interface Toast {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message?: string
  duration?: number
}

export const useAppStore = defineStore('app', () => {
  // State
  const isLoading = ref(false)
  const loadingMessage = ref('Loading...')
  const toasts = ref<Toast[]>([])
  const sidebarCollapsed = ref(false)
  const theme = ref<'light' | 'dark'>('light')

  // Getters
  const hasToasts = computed(() => toasts.value.length > 0)

  // Actions
  function setLoading(loading: boolean, message?: string) {
    isLoading.value = loading
    if (message) {
      loadingMessage.value = message
    }
  }

  function showToast(toast: Omit<Toast, 'id'>) {
    const id = `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    const newToast: Toast = {
      id,
      duration: 5000,
      ...toast
    }

    toasts.value.push(newToast)

    return id
  }

  function removeToast(id: string) {
    const index = toasts.value.findIndex(t => t.id === id)
    if (index !== -1) {
      toasts.value.splice(index, 1)
    }
  }

  function clearToasts() {
    toasts.value = []
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
    localStorage.setItem('sidebar_collapsed', String(sidebarCollapsed.value))
  }

  function setTheme(newTheme: 'light' | 'dark') {
    theme.value = newTheme
    localStorage.setItem('theme', newTheme)

    // Apply theme to document
    if (newTheme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  async function initialize() {
    // Restore sidebar state
    const savedSidebarState = localStorage.getItem('sidebar_collapsed')
    if (savedSidebarState) {
      sidebarCollapsed.value = savedSidebarState === 'true'
    }

    // Restore theme
    const savedTheme = localStorage.getItem('theme') as 'light' | 'dark' | null
    if (savedTheme) {
      setTheme(savedTheme)
    } else {
      // Detect system preference
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      setTheme(prefersDark ? 'dark' : 'light')
    }
  }

  // Convenience methods for toasts
  function success(title: string, message?: string) {
    return showToast({ type: 'success', title, message })
  }

  function error(title: string, message?: string) {
    return showToast({ type: 'error', title, message })
  }

  function warning(title: string, message?: string) {
    return showToast({ type: 'warning', title, message })
  }

  function info(title: string, message?: string) {
    return showToast({ type: 'info', title, message })
  }

  return {
    // State
    isLoading,
    loadingMessage,
    toasts,
    sidebarCollapsed,
    theme,
    // Getters
    hasToasts,
    // Actions
    setLoading,
    showToast,
    removeToast,
    clearToasts,
    toggleSidebar,
    setTheme,
    initialize,
    // Convenience methods
    success,
    error,
    warning,
    info
  }
})
