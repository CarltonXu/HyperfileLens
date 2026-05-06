import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface FavoriteItem {
  id: string
  name: string
  path: string
  icon: string
  groupId: string
}

const STORAGE_KEY = 'hyperfilelens_favorites'

// Calculate max favorites based on screen width
// Each favorite item is approximately 120px wide (icon + text + padding)
// Reserve space for: sidebar toggle (60px) + user menu (200px) + padding (100px)
const getMaxFavoritesByScreen = (): number => {
  if (typeof window === 'undefined') return 8
  
  const availableWidth = window.innerWidth - 360 // Sidebar + user menu + padding
  const itemWidth = 120 // Approximate width per item
  
  // Calculate max items, minimum 4, maximum 12
  const calculated = Math.floor(availableWidth / itemWidth)
  return Math.min(Math.max(calculated, 4), 12)
}

export const useFavoritesStore = defineStore('favorites', () => {
  const favorites = ref<FavoriteItem[]>([])
  const maxFavorites = ref(getMaxFavoritesByScreen())

  // Update max favorites on window resize
  if (typeof window !== 'undefined') {
    window.addEventListener('resize', () => {
      maxFavorites.value = getMaxFavoritesByScreen()
    })
  }

  // Check if can add more favorites
  const canAddFavorite = computed(() => favorites.value.length < maxFavorites.value)

  // Initialize from localStorage
  const loadFavorites = () => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        favorites.value = JSON.parse(stored)
      }
    } catch (e) {
      console.error('Failed to load favorites:', e)
    }
  }

  // Save to localStorage
  const saveFavorites = () => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(favorites.value))
    } catch (e) {
      console.error('Failed to save favorites:', e)
    }
  }

  // Add favorite - returns true if successful, false if limit reached
  const addFavorite = (item: FavoriteItem): boolean => {
    if (favorites.value.some(f => f.id === item.id)) {
      return true // Already exists, consider it success
    }
    
    if (!canAddFavorite.value) {
      return false // Limit reached
    }
    
    favorites.value.push(item)
    saveFavorites()
    return true
  }

  // Remove favorite
  const removeFavorite = (id: string) => {
    const index = favorites.value.findIndex(f => f.id === id)
    if (index > -1) {
      favorites.value.splice(index, 1)
      saveFavorites()
    }
  }

  // Toggle favorite - returns { success: boolean, isFavorite: boolean }
  const toggleFavorite = (item: FavoriteItem): { success: boolean; isFavorite: boolean } => {
    if (isFavorite(item.id)) {
      removeFavorite(item.id)
      return { success: true, isFavorite: false }
    } else {
      const success = addFavorite(item)
      return { success, isFavorite: success }
    }
  }

  // Check if item is favorite
  const isFavorite = (id: string): boolean => {
    return favorites.value.some(f => f.id === id)
  }

  // Clear all favorites
  const clearFavorites = () => {
    favorites.value = []
    saveFavorites()
  }

  // Load favorites on init
  loadFavorites()

  return {
    favorites,
    maxFavorites,
    canAddFavorite,
    addFavorite,
    removeFavorite,
    toggleFavorite,
    isFavorite,
    clearFavorites,
    loadFavorites
  }
})
