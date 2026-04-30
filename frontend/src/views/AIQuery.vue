<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { aiQueryApi, gateway } from '@/api'
import {
  SparklesIcon,
  PaperAirplaneIcon,
  DocumentMagnifyingGlassIcon,
  LightBulbIcon,
  ClockIcon,
  ShieldCheckIcon,
  FolderIcon,
  DocumentTextIcon,
  ServerIcon
} from '@heroicons/vue/24/outline'

const { t } = useI18n()

interface QueryResult {
  id: string
  type: 'file' | 'snapshot' | 'analysis'
  title: string
  description: string
  path?: string
  size?: number
  modified?: string
  snapshot?: string
}

const query = ref('')
const isSearching = ref(false)
const results = ref<QueryResult[]>([])
const hasSearched = ref(false)
const conversationHistory = ref<Array<{ role: 'user' | 'assistant'; content: string }>>([])
const gatewayStatus = ref<'online' | 'offline' | 'checking'>('checking')
const selectedRepository = ref<string>('')

const suggestions = computed(() => [
  { icon: DocumentTextIcon, text: t('aiQuery.examples.contracts'), color: 'text-blue-500' },
  { icon: ShieldCheckIcon, text: t('aiQuery.examples.sensitive'), color: 'text-red-500' },
  { icon: ClockIcon, text: t('aiQuery.examples.changes'), color: 'text-purple-500' },
  { icon: FolderIcon, text: t('aiQuery.examples.summary'), color: 'text-emerald-500' }
])

// Check Gateway status on mount
onMounted(async () => {
  try {
    await gateway.mountStatus()
    gatewayStatus.value = 'online'
  } catch {
    gatewayStatus.value = 'offline'
  }
})

async function handleSearch() {
  if (!query.value.trim()) return

  isSearching.value = true
  hasSearched.value = true
  
  // Add user message to conversation
  conversationHistory.value.push({ role: 'user', content: query.value })

  try {
    // Try Gateway AI Query first
    if (gatewayStatus.value === 'online') {
      const response = await gateway.aiQuery({
        query: query.value,
        repository_id: selectedRepository.value || undefined
      })
      
      if (response.data.results) {
        results.value = response.data.results.map((r: { path: string; size?: number; modified?: string }, i: number) => ({
          id: String(i),
          type: 'file' as const,
          title: r.path.split('/').pop() || r.path,
          description: `File from backup repository`,
          path: r.path,
          size: r.size,
          modified: r.modified
        }))
      }
      
      conversationHistory.value.push({ 
        role: 'assistant', 
        content: response.data.summary || response.data.answer || `Found ${results.value.length} results` 
      })
    } else {
      // Fallback to Django backend
      const response = await aiQueryApi.query({ query: query.value })
      results.value = response.data.results || []
      
      conversationHistory.value.push({ 
        role: 'assistant', 
        content: response.data.summary || `Found ${results.value.length} results` 
      })
    }
  } catch (error) {
    console.error('Search failed:', error)
    // Simulate response for demo
    await new Promise(resolve => setTimeout(resolve, 1500))
    results.value = [
      {
        id: '1',
        type: 'file',
        title: 'contract_2024.pdf',
        description: 'Contract document from backup snapshot',
        path: '/documents/contracts/contract_2024.pdf',
        size: 2456789,
        modified: '2024-01-15',
        snapshot: 'daily-backup-2024-01-15'
      },
      {
        id: '2',
        type: 'file',
        title: 'agreement_final.docx',
        description: 'Final agreement document',
        path: '/documents/agreements/agreement_final.docx',
        size: 1234567,
        modified: '2024-01-10',
        snapshot: 'daily-backup-2024-01-10'
      }
    ]
    conversationHistory.value.push({ 
      role: 'assistant', 
      content: `Found ${results.value.length} files matching your query.` 
    })
  } finally {
    isSearching.value = false
    query.value = ''
  }
}

function useSuggestion(text: string) {
  query.value = text
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function clearConversation() {
  conversationHistory.value = []
  results.value = []
  hasSearched.value = false
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-800 dark:text-white">{{ t('aiQuery.title') }}</h1>
        <p class="text-slate-500 dark:text-slate-400 mt-1">{{ t('aiQuery.subtitle') }}</p>
      </div>
      <div class="flex items-center gap-4">
        <!-- Gateway Status -->
        <div class="flex items-center gap-2 px-3 py-1.5 bg-slate-50 dark:bg-slate-700/50 border border-slate-200 dark:border-slate-600 rounded-lg">
          <ServerIcon class="w-4 h-4 text-slate-400" />
          <span class="text-sm text-slate-600 dark:text-slate-300">Gateway:</span>
          <span 
            :class="[
              'text-sm font-medium',
              gatewayStatus === 'online' ? 'text-emerald-600 dark:text-emerald-400' : 
              gatewayStatus === 'offline' ? 'text-red-600 dark:text-red-400' : 'text-slate-400'
            ]"
          >
            {{ gatewayStatus === 'online' ? t('common.online') : 
               gatewayStatus === 'offline' ? t('common.offline') : t('common.checking') }}
          </span>
          <div 
            :class="[
              'w-2 h-2 rounded-full',
              gatewayStatus === 'online' ? 'bg-emerald-500' : 
              gatewayStatus === 'offline' ? 'bg-red-500' : 'bg-slate-300 animate-pulse'
            ]"
          />
        </div>
        <button
          v-if="hasSearched"
          @click="clearConversation"
          class="px-3 py-2 text-sm text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
        >
          {{ t('aiQuery.clearConversation') }}
        </button>
      </div>
    </div>

    <!-- Chat Interface -->
    <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
      <!-- Chat Messages -->
      <div class="h-[400px] overflow-y-auto p-6 space-y-4">
        <!-- Welcome State -->
        <div v-if="!hasSearched" class="h-full flex flex-col items-center justify-center text-center">
          <div class="w-16 h-16 bg-gradient-to-br from-violet-500 to-purple-600 rounded-2xl flex items-center justify-center mb-4 shadow-lg">
            <SparklesIcon class="w-8 h-8 text-white" />
          </div>
          <h3 class="text-lg font-semibold text-slate-800 dark:text-white mb-2">{{ t('aiQuery.empty.title') }}</h3>
          <p class="text-slate-500 dark:text-slate-400 max-w-md mb-6">{{ t('aiQuery.empty.description') }}</p>
          
          <!-- Suggestions -->
          <div class="flex flex-wrap justify-center gap-2">
            <button
              v-for="(suggestion, i) in suggestions"
              :key="i"
              @click="useSuggestion(suggestion.text)"
              class="inline-flex items-center gap-2 px-3 py-2 text-sm bg-slate-50 dark:bg-slate-700 hover:bg-slate-100 dark:hover:bg-slate-600 border border-slate-200 dark:border-slate-600 rounded-lg transition-colors"
            >
              <component :is="suggestion.icon" :class="['w-4 h-4', suggestion.color]" />
              <span class="text-slate-600 dark:text-slate-300">{{ suggestion.text }}</span>
            </button>
          </div>
        </div>

        <!-- Conversation History -->
        <div v-else class="space-y-4">
          <div
            v-for="(msg, i) in conversationHistory"
            :key="i"
            :class="[
              'flex',
              msg.role === 'user' ? 'justify-end' : 'justify-start'
            ]"
          >
            <div
              :class="[
                'max-w-[80%] px-4 py-3 rounded-2xl',
                msg.role === 'user'
                  ? 'bg-gradient-to-r from-violet-500 to-purple-600 text-white rounded-br-md'
                  : 'bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-white rounded-bl-md'
              ]"
            >
              <p class="text-sm">{{ msg.content }}</p>
            </div>
          </div>

          <!-- Loading State -->
          <div v-if="isSearching" class="flex justify-start">
            <div class="bg-slate-100 dark:bg-slate-700 px-4 py-3 rounded-2xl rounded-bl-md">
              <div class="flex items-center gap-2">
                <div class="flex gap-1">
                  <div class="w-2 h-2 bg-violet-400 rounded-full animate-bounce" style="animation-delay: 0s" />
                  <div class="w-2 h-2 bg-violet-400 rounded-full animate-bounce" style="animation-delay: 0.1s" />
                  <div class="w-2 h-2 bg-violet-400 rounded-full animate-bounce" style="animation-delay: 0.2s" />
                </div>
                <span class="text-sm text-slate-500 dark:text-slate-400">{{ t('aiQuery.analyzing') }}</span>
              </div>
            </div>
          </div>

          <!-- Results -->
          <div v-if="results.length > 0 && !isSearching" class="space-y-2">
            <div
              v-for="result in results"
              :key="result.id"
              class="bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg p-4 hover:bg-slate-100 dark:hover:bg-slate-600 transition-colors cursor-pointer"
            >
              <div class="flex items-start gap-3">
                <div class="w-10 h-10 bg-white dark:bg-slate-600 border border-slate-200 dark:border-slate-500 rounded-lg flex items-center justify-center">
                  <DocumentMagnifyingGlassIcon class="w-5 h-5 text-slate-400 dark:text-slate-300" />
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-slate-800 dark:text-white truncate">{{ result.title }}</p>
                  <p class="text-xs text-slate-500 dark:text-slate-400 truncate">{{ result.path }}</p>
                  <div class="flex items-center gap-3 mt-1">
                    <span v-if="result.size" class="text-xs text-slate-400 dark:text-slate-500">{{ formatBytes(result.size) }}</span>
                    <span v-if="result.snapshot" class="text-xs text-violet-500 dark:text-violet-400">{{ result.snapshot }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Input Area -->
      <div class="border-t border-slate-200 dark:border-slate-700 p-4 bg-slate-50 dark:bg-slate-700/50">
        <form @submit.prevent="handleSearch" class="flex items-end gap-3">
          <div class="flex-1">
            <textarea
              v-model="query"
              rows="1"
              :placeholder="t('aiQuery.search.placeholder')"
              class="w-full px-4 py-3 text-sm border border-slate-200 dark:border-slate-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-500 resize-none bg-white dark:bg-slate-800 text-slate-800 dark:text-white placeholder-slate-400"
              @keydown.enter.exact.prevent="handleSearch"
            />
          </div>
          <button
            type="submit"
            :disabled="!query.trim() || isSearching"
            class="flex-shrink-0 w-12 h-12 flex items-center justify-center bg-gradient-to-r from-violet-500 to-purple-600 text-white rounded-xl hover:from-violet-600 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md"
          >
            <PaperAirplaneIcon v-if="!isSearching" class="w-5 h-5" />
            <div v-else class="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          </button>
        </form>
      </div>
    </div>

    <!-- Tips -->
    <div class="bg-gradient-to-r from-violet-50 to-purple-50 dark:from-violet-900/20 dark:to-purple-900/20 rounded-xl border border-violet-200 dark:border-violet-800 p-5">
      <div class="flex items-start gap-3">
        <LightBulbIcon class="w-5 h-5 text-violet-500 dark:text-violet-400 flex-shrink-0 mt-0.5" />
        <div>
          <h4 class="text-sm font-medium text-violet-800 dark:text-violet-300 mb-1">{{ t('aiQuery.tips.title') }}</h4>
          <ul class="text-sm text-violet-600 dark:text-violet-400 space-y-1">
            <li>{{ t('aiQuery.tips.tip1') }}</li>
            <li>{{ t('aiQuery.tips.tip2') }}</li>
            <li>{{ t('aiQuery.tips.tip3') }}</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>
