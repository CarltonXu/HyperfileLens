<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useI18n } from 'vue-i18n'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const { t, locale } = useI18n()

const isMobileMenuOpen = ref(false)
const isUserMenuOpen = ref(false)

const navigation = computed(() => [
  { name: t('nav.dashboard'), path: '/', icon: 'dashboard', current: route.path === '/' },
  { name: t('nav.nodes'), path: '/nodes', icon: 'nodes', current: route.path.startsWith('/nodes') },
  { name: t('nav.backupTasks'), path: '/backup-tasks', icon: 'backup', current: route.path === '/backup-tasks' },
  { name: t('nav.recoveryTasks'), path: '/recovery-tasks', icon: 'recovery', current: route.path === '/recovery-tasks' },
  { name: t('nav.repository'), path: '/repository', icon: 'repository', current: route.path === '/repository' },
  { name: t('nav.policies'), path: '/policies', icon: 'policies', current: route.path === '/policies' },
  { name: t('nav.aiQuery'), path: '/ai-query', icon: 'ai', current: route.path === '/ai-query' },
  { name: t('nav.auditLog'), path: '/audit-log', icon: 'audit', current: route.path === '/audit-log' },
  { name: t('nav.settings'), path: '/settings', icon: 'settings', current: route.path === '/settings' }
])

function toggleMobileMenu() {
  isMobileMenuOpen.value = !isMobileMenuOpen.value
}

function toggleUserMenu() {
  isUserMenuOpen.value = !isUserMenuOpen.value
}

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}

function setLocale(newLocale: string) {
  locale.value = newLocale
  localStorage.setItem('locale', newLocale)
}

onMounted(() => {
  // Close menus when clicking outside
  document.addEventListener('click', (e) => {
    const target = e.target as HTMLElement
    if (!target.closest('.user-menu')) {
      isUserMenuOpen.value = false
    }
  })
})
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Top Navigation Bar -->
    <nav class="bg-white border-b border-gray-200 sticky top-0 z-40">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16">
          <!-- Logo & Mobile Menu Button -->
          <div class="flex items-center">
            <button
              class="lg:hidden p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100"
              @click="toggleMobileMenu"
            >
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>

            <router-link to="/" class="flex items-center gap-3">
              <div class="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
                <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                </svg>
              </div>
              <span class="font-semibold text-gray-900 hidden sm:block">HyperFileLens</span>
            </router-link>
          </div>

          <!-- Desktop Navigation -->
          <div class="hidden lg:flex lg:items-center lg:gap-1">
            <router-link
              v-for="item in navigation"
              :key="item.path"
              :to="item.path"
              :class="[
                'nav-link',
                item.current ? 'nav-link-active' : ''
              ]"
            >
              {{ item.name }}
            </router-link>
          </div>

          <!-- Right Side -->
          <div class="flex items-center gap-4">
            <!-- Language Switcher -->
            <div class="relative">
              <select
                :value="locale"
                @change="setLocale(($event.target as HTMLSelectElement).value)"
                class="text-sm border-0 bg-transparent text-gray-600 hover:text-gray-900 focus:outline-none cursor-pointer"
              >
                <option value="en">EN</option>
                <option value="zh-CN">中文</option>
              </select>
            </div>

            <!-- User Menu -->
            <div class="relative user-menu">
              <button
                class="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-100"
                @click="toggleUserMenu"
              >
                <div class="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                  <span class="text-sm font-medium text-primary-700">
                    {{ authStore.user?.email?.[0]?.toUpperCase() || 'U' }}
                  </span>
                </div>
                <span class="hidden sm:block text-sm text-gray-700">
                  {{ authStore.userFullName }}
                </span>
                <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              <!-- User Dropdown -->
              <Transition name="fade">
                <div
                  v-if="isUserMenuOpen"
                  class="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-200 py-1"
                >
                  <div class="px-4 py-3 border-b border-gray-100">
                    <p class="text-sm font-medium text-gray-900">{{ authStore.userFullName }}</p>
                    <p class="text-xs text-gray-500">{{ authStore.user?.email }}</p>
                  </div>

                  <router-link
                    to="/settings"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    @click="isUserMenuOpen = false"
                  >
                    {{ t('nav.settings') }}
                  </router-link>

                  <button
                    class="w-full text-left px-4 py-2 text-sm text-danger-600 hover:bg-gray-100"
                    @click="handleLogout"
                  >
                    {{ t('nav.logout') }}
                  </button>
                </div>
              </Transition>
            </div>
          </div>
        </div>
      </div>

      <!-- Mobile Navigation -->
      <Transition name="slide">
        <div v-if="isMobileMenuOpen" class="lg:hidden bg-white border-b border-gray-200">
          <div class="px-4 py-3 space-y-1">
            <router-link
              v-for="item in navigation"
              :key="item.path"
              :to="item.path"
              :class="[
                'block px-3 py-2 rounded-lg text-base font-medium',
                item.current
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              ]"
              @click="isMobileMenuOpen = false"
            >
              {{ item.name }}
            </router-link>
          </div>
        </div>
      </Transition>
    </nav>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-enter-active,
.slide-leave-active {
  transition: all 0.2s ease;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
