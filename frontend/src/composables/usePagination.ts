import { computed, ref } from 'vue'

const DEFAULT_PAGE_SIZE = 10
const STORAGE_KEY = 'defaultPageSize'
const ACTIVE_PAGE_SIZE_KEY = 'activePageSize'

const readNumber = (key: string, fallback: number): number => {
  const stored = localStorage.getItem(key)
  if (!stored) return fallback
  const parsed = parseInt(stored, 10)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback
}

const defaultPageSize = ref(readNumber(STORAGE_KEY, DEFAULT_PAGE_SIZE))
const activePageSize = ref<number | null>(
  localStorage.getItem(ACTIVE_PAGE_SIZE_KEY)
    ? readNumber(ACTIVE_PAGE_SIZE_KEY, defaultPageSize.value)
    : null,
)

/**
 * 分页管理 Hook
 * 用于管理用户的分页大小偏好
 */
export function usePagination() {
  /**
   * 获取分页大小。
   * 优先使用任意页面最近选择的全局当前分页大小，其次使用设置页保存的默认分页大小。
   */
  const getPageSize = (_key: string = 'default'): number => {
    return activePageSize.value ?? getGlobalPageSize()
  }

  /**
   * 设置分页大小。
   * 任意页面修改分页大小后，作为全局当前分页大小影响后续所有页面。
   */
  const setPageSize = (size: number, _key: string = 'default'): void => {
    activePageSize.value = size
    localStorage.setItem(ACTIVE_PAGE_SIZE_KEY, String(size))
  }

  /**
   * 获取全局默认分页大小
   */
  const getGlobalPageSize = (): number => {
    return defaultPageSize.value
  }

  /**
   * 设置全局默认分页大小
   */
  const setGlobalPageSize = (size: number): void => {
    defaultPageSize.value = size
    localStorage.setItem(STORAGE_KEY, String(size))
    // 设置页保存默认值时，清除页面上临时选择的全局当前分页大小，让所有页面回到默认值。
    activePageSize.value = null
    localStorage.removeItem(ACTIVE_PAGE_SIZE_KEY)
    clearAllPageSizes()
  }

  /**
   * 清除所有页面特定的分页大小设置（不影响全局默认值）
   */
  const clearAllPageSizes = (): void => {
    Object.keys(localStorage)
      .filter(key => key.startsWith('pageSize_'))
      .forEach(key => localStorage.removeItem(key))
  }

  /**
   * 重置所有分页大小为默认值
   */
  const resetAllPageSizes = (): void => {
    defaultPageSize.value = DEFAULT_PAGE_SIZE
    activePageSize.value = null
    localStorage.removeItem(STORAGE_KEY)
    localStorage.removeItem(ACTIVE_PAGE_SIZE_KEY)
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
