import { ref, computed, watch } from 'vue'

const DEFAULT_PAGE_SIZE = 10
const STORAGE_KEY = 'defaultPageSize'

// 当前页面分页大小（可以从全局状态获取）
const currentPageSize = ref(DEFAULT_PAGE_SIZE)

/**
 * 分页管理 Hook
 * 用于管理用户的分页大小偏好
 */
export function usePagination() {
  /**
   * 获取默认分页大小（优先使用用户设置）
   */
  const getPageSize = (key: string = 'default'): number => {
    const stored = localStorage.getItem(`pageSize_${key}`)
    if (stored) {
      return parseInt(stored, 10)
    }
    return getGlobalPageSize()
  }

  /**
   * 设置分页大小
   */
  const setPageSize = (size: number, key: string = 'default'): void => {
    localStorage.setItem(`pageSize_${key}`, String(size))
  }

  /**
   * 获取全局默认分页大小
   */
  const getGlobalPageSize = (): number => {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      return parseInt(stored, 10)
    }
    return DEFAULT_PAGE_SIZE
  }

  /**
   * 设置全局默认分页大小
   */
  const setGlobalPageSize = (size: number): void => {
    localStorage.setItem(STORAGE_KEY, String(size))
    // 清除所有页面特定的分页大小设置，让所有页面回到新的默认值
    clearAllPageSizes()
  }

  /**
   * 清除所有页面特定的分页大小设置（不影响全局默认值）
   */
  const clearAllPageSizes = (): void => {
    Object.keys(localStorage)
      .filter(key => key.startsWith('pageSize_') && key !== STORAGE_KEY)
      .forEach(key => localStorage.removeItem(key))
  }

  /**
   * 重置所有分页大小为默认值
   */
  const resetAllPageSizes = (): void => {
    localStorage.removeItem(STORAGE_KEY)
    // 清除所有页面特定的分页大小设置
    Object.keys(localStorage)
      .filter(key => key.startsWith('pageSize_'))
      .forEach(key => localStorage.removeItem(key))
  }

  /**
   * 获取全局默认分页大小（响应式）
   */
  const globalPageSize = computed(() => getGlobalPageSize())

  /**
   * 设置全局默认分页大小（响应式）
   */
  const setGlobalPageSizeRef = (size: number): void => {
    setGlobalPageSize(size)
  }

  return {
    getPageSize,
    setPageSize,
    getGlobalPageSize,
    setGlobalPageSize,
    globalPageSize,
    setGlobalPageSizeRef,
    clearAllPageSizes,
    resetAllPageSizes,
    DEFAULT_PAGE_SIZE
  }
}