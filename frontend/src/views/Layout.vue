<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useI18n } from 'vue-i18n'
import ThemeSwitcher from '@/components/ThemeSwitcher.vue'
import {
  HomeIcon,
  ServerIcon,
  CloudArrowUpIcon,
  ArrowUturnLeftIcon,
  CircleStackIcon,
  ClockIcon,
  SparklesIcon,
  ClipboardDocumentListIcon,
  Cog6ToothIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ArrowRightStartOnRectangleIcon,
  LanguageIcon,
  ComputerDesktopIcon,
  Bars3Icon,
  UserCircleIcon,
  BuildingOffice2Icon,
  KeyIcon,
  UsersIcon,
  SunIcon,
  MoonIcon
} from '@heroicons/vue/24/outline'
import {
  HomeIcon as HomeIconSolid,
  ServerIcon as ServerIconSolid,
  CloudArrowUpIcon as CloudArrowUpIconSolid,
  ArrowUturnLeftIcon as ArrowUturnLeftIconSolid,
  CircleStackIcon as CircleStackIconSolid,
  ClockIcon as ClockIconSolid,
  SparklesIcon as SparklesIconSolid,
  ClipboardDocumentListIcon as ClipboardDocumentListIconSolid,
  Cog6ToothIcon as Cog6ToothIconSolid,
  BuildingOffice2Icon as BuildingOffice2IconSolid,
  KeyIcon as KeyIconSolid,
  UsersIcon as UsersIconSolid
} from '@heroicons/vue/24/solid'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const { t, locale } = useI18n()

const isCollapsed = ref(false)
const isUserMenuOpen = ref(false)
const isLangMenuOpen = ref(false)
const hoverItem = ref<string | null>(null)
const tooltipPosition = ref({ top: 0, show: false, text: '' })

// 欢迎弹窗
const showWelcome = ref(false)
const welcomeVisible = ref(false)

// 获取时间段问候语
const getGreeting = () => {
  const hour = new Date().getHours()
  if (hour >= 5 && hour < 12) {
    return { text: t('welcome.goodMorning'), icon: SunIcon, color: 'text-amber-500' }
  } else if (hour >= 12 && hour < 18) {
    return { text: t('welcome.goodAfternoon'), icon: SunIcon, color: 'text-orange-500' }
  } else {
    return { text: t('welcome.goodEvening'), icon: MoonIcon, color: 'text-indigo-400' }
  }
}

// 显示欢迎弹窗
const showWelcomeToast = () => {
  showWelcome.value = true
  setTimeout(() => {
    welcomeVisible.value = true
  }, 50)
  // 5秒后自动关闭
  setTimeout(() => {
    closeWelcome()
  }, 5000)
}

// 关闭欢迎弹窗
const closeWelcome = () => {
  welcomeVisible.value = false
  setTimeout(() => {
    showWelcome.value = false
  }, 300)
}

// Navigation items with icons
const navigation = computed(() => {
  const items = [
    {
      name: t('nav.dashboard'),
      path: '/',
      icon: HomeIcon,
      iconSolid: HomeIconSolid,
      current: route.path === '/'
    },
    {
      name: t('nav.proxies'),
      path: '/proxies',
      icon: ServerIcon,
      iconSolid: ServerIconSolid,
      current: route.path.startsWith('/proxies')
    },
    {
      name: t('nav.backupTasks'),
      path: '/backup-tasks',
      icon: CloudArrowUpIcon,
      iconSolid: CloudArrowUpIconSolid,
      current: route.path === '/backup-tasks'
    },
    {
      name: t('nav.recoveryTasks'),
      path: '/recovery-tasks',
      icon: ArrowUturnLeftIcon,
      iconSolid: ArrowUturnLeftIconSolid,
      current: route.path === '/recovery-tasks'
    },
    {
      name: t('nav.repository'),
      path: '/repository',
      icon: CircleStackIcon,
      iconSolid: CircleStackIconSolid,
      current: route.path === '/repository'
    },
    {
      name: t('nav.sourceResources'),
      path: '/source-resources',
      icon: ComputerDesktopIcon,
      iconSolid: ComputerDesktopIcon,
      current: route.path === '/source-resources'
    },
    {
      name: t('nav.policies'),
      path: '/policies',
      icon: ClockIcon,
      iconSolid: ClockIconSolid,
      current: route.path === '/policies'
    },
    {
      name: t('nav.aiInsights'),
      path: '/ai-insights',
      icon: SparklesIcon,
      iconSolid: SparklesIconSolid,
      current: route.path === '/ai-insights'
    },
    {
      name: t('nav.auditLog'),
      path: '/audit-log',
      icon: ClipboardDocumentListIcon,
      iconSolid: ClipboardDocumentListIconSolid,
      current: route.path === '/audit-log'
    },
    {
      name: t('nav.tenants'),
      path: '/tenants',
      icon: BuildingOffice2Icon,
      iconSolid: BuildingOffice2IconSolid,
      current: route.path === '/tenants',
      requiresSuperuser: true
    },
    {
      name: t('nav.users'),
      path: '/users',
      icon: UsersIcon,
      iconSolid: UsersIconSolid,
      current: route.path === '/users',
      requiresTenantAdmin: true
    },
    {
      name: t('nav.licenses'),
      path: '/licenses',
      icon: KeyIcon,
      iconSolid: KeyIconSolid,
      current: route.path === '/licenses'
    },
    {
      name: t('nav.settings'),
      path: '/settings',
      icon: Cog6ToothIcon,
      iconSolid: Cog6ToothIconSolid,
      current: route.path === '/settings'
    }
  ]

  return items.filter(item => {
    if (item.requiresSuperuser && !authStore.user?.is_superuser) {
      return false
    }
    if (item.requiresTenantAdmin) {
      const isSuperuser = authStore.user?.is_superuser
      const role = authStore.user?.tenant_role
      if (!isSuperuser && role !== 'admin') {
        return false
      }
    }
    return true
  })
})

function toggleSidebar() {
  isCollapsed.value = !isCollapsed.value
  localStorage.setItem('sidebarCollapsed', String(isCollapsed.value))
}

function toggleUserMenu() {
  isUserMenuOpen.value = !isUserMenuOpen.value
  isLangMenuOpen.value = false
}

function toggleLangMenu() {
  isLangMenuOpen.value = !isLangMenuOpen.value
  isUserMenuOpen.value = false
}

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}

function openProfile() {
  isUserMenuOpen.value = false
  router.push('/settings')
}

function setLocale(newLocale: string) {
  locale.value = newLocale
  localStorage.setItem('locale', newLocale)
  isLangMenuOpen.value = false
}

function handleMouseEnter(item: any, event: MouseEvent) {
  hoverItem.value = item.path
  if (isCollapsed.value) {
    const target = event.currentTarget as HTMLElement
    const rect = target.getBoundingClientRect()
    tooltipPosition.value = {
      top: rect.top + rect.height / 2,
      show: true,
      text: item.name
    }
  }
}

function handleMouseLeave() {
  hoverItem.value = null
  tooltipPosition.value.show = false
}

function handleClickOutside(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (!target.closest('.user-menu') && !target.closest('.lang-menu')) {
    isUserMenuOpen.value = false
    isLangMenuOpen.value = false
  }
}

onMounted(() => {
  const savedCollapsed = localStorage.getItem('sidebarCollapsed')
  if (savedCollapsed !== null) {
    isCollapsed.value = savedCollapsed === 'true'
  }
  document.addEventListener('click', handleClickOutside)
  
  // 检查是否需要显示欢迎弹窗（登录后首次进入）
  const showWelcomeFlag = sessionStorage.getItem('showWelcome')
  if (showWelcomeFlag === 'true') {
    sessionStorage.removeItem('showWelcome')
    // 延迟显示，让页面完全加载
    setTimeout(() => {
      showWelcomeToast()
    }, 500)
  }
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <div class="min-h-screen bg-slate-50 dark:bg-slate-900 flex flex-col">
    <!-- Top Header Bar -->
    <header class="fixed top-0 left-0 right-0 h-14 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 shadow-sm z-40 flex items-center justify-between px-4">
      <!-- Left: Logo & Toggle -->
      <div class="flex items-center gap-3">
        <button
          @click="toggleSidebar"
          class="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-slate-600 dark:hover:text-slate-300 transition-colors lg:hidden"
        >
          <Bars3Icon class="w-5 h-5" />
        </button>
        <div class="flex items-center gap-2">
          <div class="w-7 h-7 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center shadow-sm">
            <ComputerDesktopIcon class="w-4 h-4 text-white" />
          </div>
          <span class="font-semibold text-slate-800 dark:text-white text-sm hidden sm:block">HyperFileLens</span>
        </div>
      </div>

      <!-- Right: Theme, Language Switcher & User Menu -->
      <div class="flex items-center gap-1">
        <!-- Theme Switcher -->
        <ThemeSwitcher />

        <!-- Language Switcher -->
        <div class="relative lang-menu">
          <button
            @click="toggleLangMenu"
            class="flex items-center gap-2 px-3 py-1.5 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 hover:text-slate-900 dark:hover:text-white transition-colors"
          >
            <LanguageIcon class="w-4 h-4" />
            <span class="text-sm font-medium">
              {{ locale === 'zh-CN' ? '中文' : 'EN' }}
            </span>
          </button>

          <!-- Language Dropdown -->
          <Transition name="dropdown">
            <div
              v-if="isLangMenuOpen"
              class="absolute right-0 top-full mt-1 bg-white dark:bg-slate-800 rounded-lg shadow-lg border border-slate-200 dark:border-slate-700 z-50 w-32"
            >
              <button
                @click="setLocale('en')"
                :class="[
                  'flex items-center gap-2 w-full px-3 py-2 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 first:rounded-t-lg',
                  locale === 'en' ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400' : ''
                ]"
              >
                <span class="w-6 text-center">EN</span>
                <span>English</span>
              </button>
              <button
                @click="setLocale('zh-CN')"
                :class="[
                  'flex items-center gap-2 w-full px-3 py-2 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 last:rounded-b-lg',
                  locale === 'zh-CN' ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400' : ''
                ]"
              >
                <span class="w-6 text-center">中</span>
                <span>中文</span>
              </button>
            </div>
          </Transition>
        </div>

        <!-- User Menu -->
        <div class="relative user-menu">
          <button
            @click="toggleUserMenu"
            :class="[
              'flex items-center gap-2 px-2 py-1.5 rounded-lg transition-colors',
              isUserMenuOpen ? 'bg-slate-100 dark:bg-slate-700' : 'hover:bg-slate-50 dark:hover:bg-slate-700'
            ]"
          >
            <div class="w-7 h-7 bg-gradient-to-br from-indigo-400 to-purple-500 rounded-full flex items-center justify-center shadow-sm">
              <span class="text-xs font-medium text-white">
                {{ authStore.user?.email?.[0]?.toUpperCase() || 'U' }}
              </span>
            </div>
            <div class="text-left hidden sm:block">
              <p class="text-sm font-medium text-slate-800 dark:text-white">
                {{ authStore.userFullName }}
              </p>
            </div>
          </button>

          <!-- User Dropdown -->
          <Transition name="dropdown">
            <div
              v-if="isUserMenuOpen"
              class="absolute right-0 top-full mt-1 bg-white dark:bg-slate-800 rounded-lg shadow-lg border border-slate-200 dark:border-slate-700 z-50 w-56"
            >
              <div class="px-3 py-2 border-b border-slate-100 dark:border-slate-700">
                <p class="text-sm font-medium text-slate-800 dark:text-white truncate">{{ authStore.userFullName }}</p>
                <p class="text-xs text-slate-400 truncate">{{ authStore.user?.email }}</p>
                <p class="text-xs text-slate-400 truncate">{{ authStore.user?.role?.name || 'User' }}</p>
              </div>
              <div class="py-1 border-b border-slate-100 dark:border-slate-700">
                <button
                  @click="openProfile"
                  class="flex items-center gap-2 w-full px-3 py-2 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700"
                >
                  <UserCircleIcon class="w-4 h-4" />
                  <span>{{ t('settings.profile.title') }}</span>
                </button>
              </div>
              <button
                @click="handleLogout"
                class="flex items-center gap-2 w-full px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-b-lg"
              >
                <ArrowRightStartOnRectangleIcon class="w-4 h-4" />
                <span>{{ t('nav.logout') }}</span>
              </button>
            </div>
          </Transition>
        </div>
      </div>
    </header>

    <!-- Main Layout: Sidebar + Content -->
    <div class="flex flex-1 pt-14">
      <!-- Left Sidebar -->
      <aside
        :class="[
          'fixed left-0 top-14 h-[calc(100vh-3.5rem)] bg-white dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700 shadow-lg z-30 transition-all duration-300 ease-in-out flex flex-col',
          isCollapsed ? 'w-16' : 'w-64'
        ]"
      >
        <!-- Navigation -->
        <nav class="flex-1 py-4 overflow-y-auto">
          <ul class="space-y-1 px-2">
            <li v-for="item in navigation" :key="item.path">
              <router-link
                :to="item.path"
                :class="[
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 relative group',
                  item.current
                    ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400'
                    : 'text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 hover:text-slate-900 dark:hover:text-white'
                ]"
                @mouseenter="(e) => handleMouseEnter(item, e)"
                @mouseleave="handleMouseLeave"
              >
                <component
                  :is="item.current ? item.iconSolid : item.icon"
                  :class="[
                    'w-5 h-5 flex-shrink-0 transition-colors',
                    item.current ? 'text-indigo-600 dark:text-indigo-400' : 'text-slate-400 dark:text-slate-500 group-hover:text-slate-600 dark:group-hover:text-slate-300'
                  ]"
                />
                <Transition name="fade">
                  <span v-if="!isCollapsed" class="text-sm font-medium truncate">
                    {{ item.name }}
                  </span>
                </Transition>
                
                <!-- Active indicator -->
                <div
                  v-if="item.current"
                  class="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-indigo-600 dark:bg-indigo-400 rounded-r-full"
                />
              </router-link>
            </li>
          </ul>
        </nav>

        <!-- Collapse Button -->
        <div class="border-t border-slate-100 dark:border-slate-700 p-2">
          <button
            @click="toggleSidebar"
            class="flex items-center justify-center w-full px-3 py-2.5 rounded-lg text-slate-400 dark:text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-700 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
          >
            <component
              :is="isCollapsed ? ChevronRightIcon : ChevronLeftIcon"
              class="w-5 h-5"
            />
          </button>
        </div>
      </aside>

      <!-- Main Content Area -->
      <main
        :class="[
          'flex-1 transition-all duration-300 ease-in-out',
          isCollapsed ? 'ml-16' : 'ml-64'
        ]"
      >
        <div class="p-6 lg:p-8">
          <router-view />
        </div>
      </main>
    </div>

    <!-- Welcome Toast -->
    <Transition name="welcome">
      <div
        v-if="showWelcome"
        :class="[
          'fixed top-20 right-6 z-[9999] transition-all duration-300',
          welcomeVisible ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-4'
        ]"
      >
        <div class="bg-white dark:bg-slate-800 rounded-xl shadow-2xl border border-slate-200 dark:border-slate-700 p-4 max-w-sm">
          <div class="flex items-start gap-3">
            <!-- Avatar -->
            <div class="w-10 h-10 bg-gradient-to-br from-indigo-400 to-purple-500 rounded-full flex items-center justify-center shadow-sm flex-shrink-0">
              <span class="text-sm font-semibold text-white">
                {{ authStore.user?.email?.[0]?.toUpperCase() || 'U' }}
              </span>
            </div>
            <!-- Content -->
            <div class="flex-1 min-w-0">
              <p class="text-sm font-semibold text-slate-800 dark:text-white">
                {{ authStore.userFullName }}
              </p>
              <div class="flex items-center gap-1.5 mt-1">
                <component
                  :is="getGreeting().icon"
                  :class="['w-4 h-4', getGreeting().color]"
                />
                <span class="text-sm text-slate-500 dark:text-slate-400">
                  {{ getGreeting().text }}
                </span>
              </div>
              <p class="text-xs text-slate-400 dark:text-slate-500 mt-2">
                {{ t('welcome.subtitle') }}
              </p>
            </div>
            <!-- Close Button -->
            <button
              @click="closeWelcome"
              class="p-1 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
            >
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Global Tooltip for collapsed sidebar -->
    <Transition name="tooltip">
      <div
        v-if="tooltipPosition.show"
        class="fixed bg-slate-800 dark:bg-slate-700 text-white text-xs px-3 py-1.5 rounded-md whitespace-nowrap shadow-xl z-[9999] pointer-events-none"
        :style="{ left: '68px', top: `${tooltipPosition.top}px`, transform: 'translateY(-50%)' }"
      >
        {{ tooltipPosition.text }}
        <div class="absolute left-0 top-1/2 -translate-x-1 -translate-y-1/2 w-2 h-2 bg-slate-800 dark:bg-slate-700 rotate-45" />
      </div>
    </Transition>

  </div>
</template>

<style scoped>
/* Welcome toast transition */
.welcome-enter-active,
.welcome-leave-active {
  transition: all 0.3s ease;
}
.welcome-enter-from,
.welcome-leave-to {
  opacity: 0;
  transform: translateX(16px);
}

/* Fade transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Tooltip transition */
.tooltip-enter-active,
.tooltip-leave-active {
  transition: all 0.15s ease;
}
.tooltip-enter-from,
.tooltip-leave-to {
  opacity: 0;
  transform: translateX(-8px) translateY(-50%);
}
.tooltip-enter-to,
.tooltip-leave-from {
  transform: translateX(0) translateY(-50%);
}

/* Dropdown transition */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: all 0.2s ease;
}
.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* Scrollbar styling */
aside::-webkit-scrollbar {
  width: 4px;
}
aside::-webkit-scrollbar-track {
  background: transparent;
}
aside::-webkit-scrollbar-thumb {
  background: #e2e8f0;
  border-radius: 2px;
}
.dark aside::-webkit-scrollbar-thumb {
  background: #475569;
}
aside::-webkit-scrollbar-thumb:hover {
  background: #cbd5e1;
}
.dark aside::-webkit-scrollbar-thumb:hover {
  background: #64748b;
}
</style>
