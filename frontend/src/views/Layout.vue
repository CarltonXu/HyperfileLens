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
  ChevronDownIcon,
  ArrowRightStartOnRectangleIcon,
  LanguageIcon,
  ComputerDesktopIcon,
  UserCircleIcon,
  BuildingOffice2Icon,
  KeyIcon,
  UsersIcon,
  SunIcon,
  MoonIcon,
  BellIcon,
  ExclamationTriangleIcon
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
  UsersIcon as UsersIconSolid,
  BellIcon as BellIconSolid,
  ExclamationTriangleIcon as ExclamationTriangleIconSolid
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
const expandedGroups = ref<string[]>(['overview', 'data-protection', 'ai-insights'])

// 菜单项类型定义
interface MenuItem {
  name: string
  path: string
  icon: any
  iconSolid?: any
  current: boolean
  requiresSuperuser?: boolean
  requiresTenantAdmin?: boolean
  subItems?: { name: string; path: string; current: boolean }[]
}

interface NavigationGroup {
  id: string
  title: string
  items: MenuItem[]
}

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

// 切换分组展开状态
const toggleGroup = (groupId: string) => {
  if (isCollapsed.value) return
  const index = expandedGroups.value.indexOf(groupId)
  if (index > -1) {
    expandedGroups.value.splice(index, 1)
  } else {
    expandedGroups.value.push(groupId)
  }
}

// 检查分组是否展开
const isGroupExpanded = (groupId: string) => {
  return expandedGroups.value.includes(groupId)
}

// 导航分组
const navigationGroups = computed<NavigationGroup[]>(() => {
  const groups = [
    {
      id: 'overview',
      title: t('navGroups.overview'),
      items: [
        {
          name: t('nav.dashboard'),
          path: '/',
          icon: HomeIcon,
          iconSolid: HomeIconSolid,
          current: route.path === '/'
        }
      ]
    },
    {
      id: 'data-protection',
      title: t('navGroups.dataProtection'),
      items: [
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
          name: t('nav.policies'),
          path: '/policies',
          icon: ClockIcon,
          iconSolid: ClockIconSolid,
          current: route.path === '/policies'
        }
      ]
    },
    {
      id: 'resources',
      title: t('navGroups.resources'),
      items: [
        {
          name: t('nav.proxies'),
          path: '/proxies',
          icon: ServerIcon,
          iconSolid: ServerIconSolid,
          current: route.path.startsWith('/proxies')
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
        }
      ]
    },
    {
      id: 'ai-insights',
      title: t('navGroups.aiInsights'),
      items: [
        {
          name: t('nav.aiInsights'),
          path: '/ai-insights',
          icon: SparklesIcon,
          iconSolid: SparklesIconSolid,
          current: route.path === '/ai-insights',
          subItems: [
            { name: t('aiInsights.nav.overview'), path: '/ai-insights/overview', current: route.path === '/ai-insights/overview' || route.path === '/ai-insights' },
            { name: t('aiInsights.nav.smartSearch'), path: '/ai-insights/smart-search', current: route.path === '/ai-insights/smart-search' },
            { name: t('aiInsights.nav.sensitiveData'), path: '/ai-insights/sensitive-data', current: route.path === '/ai-insights/sensitive-data' },
            { name: t('aiInsights.nav.contentProfiling'), path: '/ai-insights/content-profiling', current: route.path === '/ai-insights/content-profiling' },
            { name: t('aiInsights.nav.dataHeatmap'), path: '/ai-insights/data-heatmap', current: route.path === '/ai-insights/data-heatmap' },
            { name: t('aiInsights.nav.redundancy'), path: '/ai-insights/redundancy', current: route.path === '/ai-insights/redundancy' },
            { name: t('aiInsights.nav.aiChat'), path: '/ai-insights/ai-chat', current: route.path === '/ai-insights/ai-chat' }
          ]
        }
      ]
    },
    {
      id: 'ops-monitor',
      title: t('navGroups.opsMonitor'),
      items: [
        {
          name: t('nav.auditLog'),
          path: '/audit-log',
          icon: ClipboardDocumentListIcon,
          iconSolid: ClipboardDocumentListIconSolid,
          current: route.path === '/audit-log'
        },
        {
          name: t('nav.eventLog'),
          path: '/event-log',
          icon: BellIcon,
          iconSolid: BellIconSolid,
          current: route.path === '/event-log'
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
          name: t('nav.alerts'),
          path: '/alerts',
          icon: ExclamationTriangleIcon,
          iconSolid: ExclamationTriangleIconSolid,
          current: route.path === '/alerts'
        }
      ]
    },
    {
      id: 'system',
      title: t('navGroups.system'),
      items: [
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
    }
  ]

  // 过滤权限
  return (groups as NavigationGroup[]).map(group => ({
    ...group,
    items: group.items.filter(item => {
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
  })).filter(group => group.items.length > 0)
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

// 处理欢迎弹窗
onMounted(() => {
  const collapsed = localStorage.getItem('sidebarCollapsed')
  if (collapsed === 'true') {
    isCollapsed.value = true
  }
  
  // 显示欢迎弹窗
  if (sessionStorage.getItem('showWelcome') === 'true') {
    sessionStorage.removeItem('showWelcome')
    setTimeout(() => {
      showWelcomeToast()
    }, 500)
  }
})

onUnmounted(() => {
  document.removeEventListener('click', () => {})
})
</script>

<template>
  <div class="min-h-screen bg-slate-50 dark:bg-slate-900">
    <!-- Sidebar -->
    <aside
      :class="[
        'fixed left-0 top-0 z-40 h-screen transition-all duration-300 ease-in-out',
        'bg-white dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700',
        isCollapsed ? 'w-16' : 'w-64'
      ]"
    >
      <!-- Logo -->
      <div class="flex items-center justify-between h-16 px-4 border-b border-slate-200 dark:border-slate-700">
        <div class="flex items-center gap-2" v-if="!isCollapsed">
          <div class="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
            <CloudArrowUpIcon class="w-5 h-5 text-white" />
          </div>
          <span class="font-bold text-slate-900 dark:text-white text-lg">HyperFileLens</span>
        </div>
        <div v-else class="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center mx-auto">
          <CloudArrowUpIcon class="w-5 h-5 text-white" />
        </div>
        <button
          @click="toggleSidebar"
          class="p-1.5 rounded-lg text-slate-500 hover:text-slate-700 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-200 dark:hover:bg-slate-700"
        >
          <ChevronLeftIcon v-if="!isCollapsed" class="w-4 h-4" />
          <ChevronRightIcon v-else class="w-4 h-4" />
        </button>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 px-2 py-4 space-y-1 overflow-y-auto h-[calc(100vh-4rem)]">
        <template v-for="group in navigationGroups" :key="group.id">
          <!-- Group Header -->
          <div
            v-if="!isCollapsed"
            @click="toggleGroup(group.id)"
            class="flex items-center justify-between px-3 py-2 text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider cursor-pointer hover:text-slate-500 dark:hover:text-slate-400"
          >
            <span>{{ group.title }}</span>
            <ChevronDownIcon
              :class="[
                'w-4 h-4 transition-transform duration-200',
                isGroupExpanded(group.id) ? 'rotate-0' : '-rotate-90'
              ]"
            />
          </div>

          <!-- Group Items -->
          <div v-show="isCollapsed || isGroupExpanded(group.id)" class="space-y-0.5">
            <div v-for="item in group.items" :key="item.path">
              <router-link
                :to="item.path"
                @mouseenter="handleMouseEnter(item, $event)"
                @mouseleave="handleMouseLeave"
                :class="[
                  'group flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                  item.current
                    ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                    : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
                ]"
              >
                <component
                  :is="item.current ? item.iconSolid : item.icon"
                  :class="[
                    'w-5 h-5 flex-shrink-0',
                    item.current ? 'text-blue-500 dark:text-blue-400' : 'text-slate-400 group-hover:text-slate-500 dark:group-hover:text-slate-400'
                  ]"
                />
                <span v-if="!isCollapsed">{{ item.name }}</span>
              </router-link>
              
              <!-- Sub Items -->
              <div v-if="!isCollapsed && item.subItems && item.subItems.length > 0" class="ml-4 mt-1 space-y-0.5">
                <router-link
                  v-for="subItem in item.subItems"
                  :key="subItem.path"
                  :to="subItem.path"
                  :class="[
                    'group flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors',
                    subItem.current
                      ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-medium'
                      : 'text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-slate-700 dark:hover:text-slate-300'
                  ]"
                >
                  <span class="w-1.5 h-1.5 rounded-full" :class="subItem.current ? 'bg-blue-500' : 'bg-slate-300 dark:bg-slate-600'"></span>
                  {{ subItem.name }}
                </router-link>
              </div>
            </div>
          </div>

          <!-- Divider -->
          <div v-if="!isCollapsed && group.id !== 'system'" class="my-3 border-t border-slate-200 dark:border-slate-700"></div>
        </template>
      </nav>

      <!-- Tooltip for collapsed sidebar -->
      <Transition
        enter-active-class="transition ease-out duration-100"
        enter-from-class="opacity-0 translate-x-2"
        enter-to-class="opacity-100 translate-x-0"
        leave-active-class="transition ease-in duration-75"
        leave-from-class="opacity-100 translate-x-0"
        leave-to-class="opacity-0 translate-x-2"
      >
        <div
          v-if="tooltipPosition.show"
          class="fixed left-20 z-50 px-3 py-1.5 text-sm font-medium text-white bg-slate-800 dark:bg-slate-700 rounded-lg shadow-lg whitespace-nowrap"
          :style="{ top: tooltipPosition.top + 'px', transform: 'translateY(-50%)' }"
        >
          {{ tooltipPosition.text }}
        </div>
      </Transition>
    </aside>

    <!-- Main Content -->
    <div
      :class="[
        'transition-all duration-300',
        isCollapsed ? 'ml-16' : 'ml-64'
      ]"
    >
      <!-- Header -->
      <header class="sticky top-0 z-30 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
        <div class="flex items-center justify-between h-16 px-6">
          <div class="flex items-center gap-4">
            <h1 class="text-lg font-semibold text-slate-900 dark:text-white">
              {{ $route.meta.title || 'HyperFileLens' }}
            </h1>
          </div>

          <div class="flex items-center gap-4">
            <!-- Theme Switcher -->
            <ThemeSwitcher />

            <!-- Language Switcher -->
            <div class="relative">
              <button
                @click="toggleLangMenu"
                class="flex items-center gap-2 p-2 rounded-lg text-slate-500 hover:text-slate-700 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-200 dark:hover:bg-slate-700"
              >
                <LanguageIcon class="w-5 h-5" />
                <span class="text-sm">{{ locale === 'zh-CN' ? '中文' : 'EN' }}</span>
              </button>
              <Transition
                enter-active-class="transition ease-out duration-100"
                enter-from-class="opacity-0 scale-95"
                enter-to-class="opacity-100 scale-100"
                leave-active-class="transition ease-in duration-75"
                leave-from-class="opacity-100 scale-100"
                leave-to-class="opacity-0 scale-95"
              >
                <div
                  v-if="isLangMenuOpen"
                  class="absolute right-0 mt-2 w-32 bg-white dark:bg-slate-800 rounded-lg shadow-lg border border-slate-200 dark:border-slate-700 py-1"
                >
                  <button
                    @click="setLocale('zh-CN')"
                    :class="[
                      'w-full px-4 py-2 text-left text-sm hover:bg-slate-100 dark:hover:bg-slate-700',
                      locale === 'zh-CN' ? 'text-blue-600 dark:text-blue-400 font-medium' : 'text-slate-700 dark:text-slate-300'
                    ]"
                  >
                    中文
                  </button>
                  <button
                    @click="setLocale('en')"
                    :class="[
                      'w-full px-4 py-2 text-left text-sm hover:bg-slate-100 dark:hover:bg-slate-700',
                      locale === 'en' ? 'text-blue-600 dark:text-blue-400 font-medium' : 'text-slate-700 dark:text-slate-300'
                    ]"
                  >
                    English
                  </button>
                </div>
              </Transition>
            </div>

            <!-- User Menu -->
            <div class="relative">
              <button
                @click="toggleUserMenu"
                class="flex items-center gap-2 p-2 rounded-lg text-slate-500 hover:text-slate-700 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-200 dark:hover:bg-slate-700"
              >
                <UserCircleIcon class="w-6 h-6" />
                <span class="text-sm font-medium">{{ authStore.user?.full_name || authStore.user?.email }}</span>
              </button>
              <Transition
                enter-active-class="transition ease-out duration-100"
                enter-from-class="opacity-0 scale-95"
                enter-to-class="opacity-100 scale-100"
                leave-active-class="transition ease-in duration-75"
                leave-from-class="opacity-100 scale-100"
                leave-to-class="opacity-0 scale-95"
              >
                <div
                  v-if="isUserMenuOpen"
                  class="absolute right-0 mt-2 w-48 bg-white dark:bg-slate-800 rounded-lg shadow-lg border border-slate-200 dark:border-slate-700 py-1"
                >
                  <button
                    @click="openProfile"
                    class="w-full px-4 py-2 text-left text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center gap-2"
                  >
                    <Cog6ToothIcon class="w-4 h-4" />
                    {{ t('nav.settings') }}
                  </button>
                  <hr class="my-1 border-slate-200 dark:border-slate-700" />
                  <button
                    @click="handleLogout"
                    class="w-full px-4 py-2 text-left text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-2"
                  >
                    <ArrowRightStartOnRectangleIcon class="w-4 h-4" />
                    {{ t('common.logout') }}
                  </button>
                </div>
              </Transition>
            </div>
          </div>
        </div>
      </header>

      <!-- Page Content -->
      <main class="p-6">
        <router-view />
      </main>
    </div>

    <!-- Welcome Popup -->
    <Transition
      enter-active-class="transition ease-out duration-300"
      enter-from-class="opacity-0 translate-x-full"
      enter-to-class="opacity-100 translate-x-0"
      leave-active-class="transition ease-in duration-200"
      leave-from-class="opacity-100 translate-x-0"
      leave-to-class="opacity-0 translate-x-full"
    >
      <div
        v-if="showWelcome"
        v-show="welcomeVisible"
        class="fixed top-20 right-6 z-50 w-80 bg-white dark:bg-slate-800 rounded-xl shadow-2xl border border-slate-200 dark:border-slate-700 overflow-hidden"
      >
        <div class="bg-gradient-to-r from-blue-500 to-purple-600 px-4 py-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <component :is="getGreeting().icon" :class="['w-5 h-5', getGreeting().color]" />
              <span class="text-white font-medium">{{ getGreeting().text }}</span>
            </div>
            <button
              @click="closeWelcome"
              class="text-white/80 hover:text-white"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
        <div class="px-4 py-3">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-blue-400 to-purple-500 rounded-full flex items-center justify-center text-white font-bold text-lg">
              {{ (authStore.user?.full_name || authStore.user?.email || 'U')[0].toUpperCase() }}
            </div>
            <div>
              <div class="font-medium text-slate-900 dark:text-white">{{ authStore.user?.full_name || authStore.user?.email }}</div>
              <div class="text-sm text-slate-500 dark:text-slate-400">{{ t('welcome.subtitle') }}</div>
            </div>
          </div>
        </div>
        <div class="bg-slate-50 dark:bg-slate-900/50 px-4 py-2 text-xs text-slate-400 dark:text-slate-500 text-center">
          HyperFileLens · {{ t('welcome.subtitle') }}
        </div>
      </div>
    </Transition>
  </div>
</template>
