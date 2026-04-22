<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const query = ref('')
const isSearching = ref(false)
const results = ref<any[]>([])
const hasSearched = ref(false)

const examples = [
  { key: 'contracts', icon: 'file' },
  { key: 'sensitive', icon: 'shield' },
  { key: 'changes', icon: 'clock' },
  { key: 'summary', icon: 'document' }
]

async function handleSearch() {
  if (!query.value.trim()) return

  isSearching.value = true
  hasSearched.value = true

  try {
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1500))
    results.value = []
  } catch (error) {
    console.error('Search failed:', error)
  } finally {
    isSearching.value = false
  }
}

function useExample(key: string) {
  query.value = t(`aiQuery.examples.${key}`)
}
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-2xl font-bold text-gray-900">{{ t('aiQuery.title') }}</h1>
      <p class="text-gray-500 mt-1">{{ t('aiQuery.subtitle') }}</p>
    </div>

    <!-- Search Box -->
    <div class="card p-6">
      <form @submit.prevent="handleSearch" class="space-y-4">
        <div class="relative">
          <textarea
            v-model="query"
            rows="3"
            class="input resize-none"
            :placeholder="t('aiQuery.search.placeholder')"
          ></textarea>
        </div>
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-sm text-gray-500">{{ t('aiQuery.search.examples') }}:</span>
            <button
              v-for="example in examples"
              :key="example.key"
              type="button"
              class="text-sm text-primary-600 hover:text-primary-700"
              @click="useExample(example.key)"
            >
              {{ t(`aiQuery.examples.${example.key}`) }}
            </button>
          </div>
          <button type="submit" class="btn-primary" :disabled="!query.trim() || isSearching">
            <span v-if="isSearching" class="spinner-sm mr-2"></span>
            {{ t('aiQuery.search.submit') }}
          </button>
        </div>
      </form>
    </div>

    <!-- Results -->
    <div v-if="hasSearched" class="card">
      <div class="card-header">
        <h3 class="text-lg font-semibold text-gray-900">{{ t('aiQuery.results.title') }}</h3>
      </div>
      <div class="card-body">
        <div v-if="isSearching" class="text-center py-8">
          <div class="spinner-lg mx-auto mb-4"></div>
          <p class="text-gray-500">Analyzing backup data...</p>
        </div>
        <div v-else-if="results.length === 0" class="text-center py-8">
          <p class="text-gray-500">{{ t('common.noData') }}</p>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="card p-8">
      <div class="text-center">
        <div class="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg class="w-8 h-8 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        </div>
        <h3 class="text-lg font-medium text-gray-900">{{ t('aiQuery.empty.title') }}</h3>
        <p class="text-gray-500 mt-2">{{ t('aiQuery.empty.description') }}</p>
      </div>
    </div>
  </div>
</template>
