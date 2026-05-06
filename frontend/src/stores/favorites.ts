import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface FavoriteItem {
  id: string
  name: string
  path: string
  icon: string
  groupId: string
}

const STORAGE_KEY = 'hyperfilelens_favorites'

export const useFavoritesStore = defineStore('favorites', () => {
  const favorites = ref<FavoriteItem[]>([])

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

  // Add favorite
  const addFavorite = (item: FavoriteItem) => {
    if (!favorites.value.some(f => f.id === item.id)) {
      favorites.value.push(item)
      saveFavorites()
    }
  }

  // Remove favorite
  const removeFavorite = (id: string) => {
    const index = favorites.value.findIndex(f => f.id === id)
    if (index > -1) {
      favorites.value.splice(index, 1)
      saveFavorites()
    }
  }

  // Toggle favorite
  const toggleFavorite = (item: FavoriteItem) => {
    if (isFavorite(item.id)) {
      removeFavorite(item.id)
    } else {
      addFavorite(item)
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
    addFavorite,
    removeFavorite,
    toggleFavorite,
    isFavorite,
    clearFavorites,
    loadFavorites
  }
})
