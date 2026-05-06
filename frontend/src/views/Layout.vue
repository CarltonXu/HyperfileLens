<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useFavoritesStore } from '@/stores/favorites'
import type { FavoriteItem } from '@/stores/favorites'
import { useI18n } from 'vue-i18n'
import ThemeSwitcher from '@/components/ThemeSwitcher.vue'
import {
  HomeIcon,
  ServerIcon,
  CloudArrowUpIcon,
  ArrowUturnLeftIcon,
  CircleStackIcon,
  ClockIcon,
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
  ExclamationTriangleIcon,
  CloudIcon,
  StarIcon,
  XMarkIcon,
  // AI Insights 三级菜单图标
  ChartBarIcon,
  MagnifyingGlassIcon,
  ShieldCheckIcon,
  DocumentChartBarIcon,
  FireIcon,
  DocumentDuplicateIcon,
  ChatBubbleLeftRightIcon
} from '@heroicons/vue/24/outline'
import {
  HomeIcon as HomeIconSolid,
  ServerIcon as ServerIconSolid,
  CloudArrowUpIcon as CloudArrowUpIconSolid,
  ArrowUturnLeftIcon as ArrowUturnLeftIconSolid,
  CircleStackIcon as CircleStackIconSolid,
  ClockIcon as ClockIconSolid,
  ClipboardDocumentListIcon as ClipboardDocumentListIconSolid,
  Cog6ToothIcon as Cog6ToothIconSolid,
  BuildingOffice2Icon as BuildingOffice2IconSolid,
  KeyIcon as KeyIconSolid,
  UsersIcon as UsersIconSolid,
  BellIcon as BellIconSolid,
  ExclamationTriangleIcon as ExclamationTriangleIconSolid,
  CloudIcon as CloudIconSolid,
  // AI Insights 三级菜单图标
  ChartBarIcon as ChartBarIconSolid,
  MagnifyingGlassIcon as MagnifyingGlassIconSolid,
  ShieldCheckIcon as ShieldCheckIconSolid,
  DocumentChartBarIcon as DocumentChartBarIconSolid,
  FireIcon as FireIconSolid,
  DocumentDuplicateIcon as DocumentDuplicateIconSolid,
  ChatBubbleLeftRightIcon as ChatBubbleLeftRightIconSolid
} from '@heroicons/vue/24/solid'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const favoritesStore = useFavoritesStore()
const { t, locale } = useI18n()

const isCollapsed = ref(false)
const isUserMenuOpen = ref(false)
const isLangMenuOpen = ref(false)
const expandedGroups = ref<string[]>(['overview', 'data-protection', 'ai-insights'])

// 收起状态下的弹出菜单
const activePopup = ref<string | null>(null)
const popupPosition = ref({ top: 0 })

// 菜单项类型定义
interface MenuItem {
  name: string
  path: string
  icon: any
  iconSolid?: any
  current: boolean
  requiresSuperuser?: boolean
  requiresTenantAdmin?: boolean
  subItems?: SubMenuItem[]
}

interface SubMenuItem {
  name: string
  path: string
  icon: any
  iconSolid?: any
  current: boolean
}

// AI Insights 二级分类（固定标签，不可点击）
interface AIInsightsSubItem {
  name: string
  path: string
  current: boolean
  icon: any
  iconSolid?: any
}

interface AIInsightsCategory {
  name: string  // 分类名称
  items: AIInsightsSubItem[]  // 三级菜单
}

interface NavigationGroup {
  id: string
  title: string
  items: MenuItem[]
  // AI Insights 特殊的三级菜单结构
  aiInsightsCategories?: AIInsightsCategory[]
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
        },
        {
          name: t('nav.gateways'),
          path: '/gateways',
          icon: CloudIcon,
          iconSolid: CloudIconSolid,
          current: route.path === '/gateways'
        }
      ]
    },
    {
      id: 'ai-insights',
      title: t('navGroups.aiInsights'),
      items: [],
      // AI Insights 特殊的三级菜单结构
      aiInsightsCategories: [
        {
          name: t('aiInsights.menuCategories.discovery'),
          items: [
            { 
              name: t('aiInsights.nav.overview'), 
              path: '/ai-insights/overview', 
              current: route.path === '/ai-insights/overview' || route.path === '/ai-insights',
              icon: ChartBarIcon,
              iconSolid: ChartBarIconSolid
            },
            { 
              name: t('aiInsights.nav.smartSearch'), 
              path: '/ai-insights/smart-search', 
              current: route.path === '/ai-insights/smart-search',
              icon: MagnifyingGlassIcon,
              iconSolid: MagnifyingGlassIconSolid
            }
          ]
        },
        {
          name: t('aiInsights.menuCategories.contentSecurity'),
          items: [
            { 
              name: t('aiInsights.nav.sensitiveData'), 
              path: '/ai-insights/sensitive-data', 
              current: route.path === '/ai-insights/sensitive-data',
              icon: ShieldCheckIcon,
              iconSolid: ShieldCheckIconSolid
            },
            { 
              name: t('aiInsights.nav.contentProfile'), 
              path: '/ai-insights/content-profiling', 
              current: route.path === '/ai-insights/content-profiling',
              icon: DocumentChartBarIcon,
              iconSolid: DocumentChartBarIconSolid
            }
          ]
        },
        {
          name: t('aiInsights.menuCategories.governance'),
          items: [
            { 
              name: t('aiInsights.nav.dataHeatmap'), 
              path: '/ai-insights/data-heatmap', 
              current: route.path === '/ai-insights/data-heatmap',
              icon: FireIcon,
              iconSolid: FireIconSolid
            },
            { 
              name: t('aiInsights.nav.redundancy'), 
              path: '/ai-insights/redundancy', 
              current: route.path === '/ai-insights/redundancy',
              icon: DocumentDuplicateIcon,
              iconSolid: DocumentDuplicateIconSolid
            }
          ]
        },
        {
          name: t('aiInsights.menuCategories.knowledge'),
          items: [
            { 
              name: t('aiInsights.nav.aiChat'), 
              path: '/ai-insights/ai-chat', 
              current: route.path === '/ai-insights/ai-chat',
              icon: ChatBubbleLeftRightIcon,
              iconSolid: ChatBubbleLeftRightIconSolid
            }
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
  })).filter(group => group.items.length > 0 || (group.aiInsightsCategories && group.aiInsightsCategories.length > 0))
})

// 获取当前路由所在的分组ID
const currentGroup = computed(() => {
  for (const group of navigationGroups.value) {
    // 检查普通菜单项
    for (const item of group.items) {
      if (item.current) return group.id
      // 检查子菜单
      if (item.subItems) {
        for (const subItem of item.subItems) {
          if (route.path === subItem.path) return group.id
        }
      }
    }
    // 检查 AI Insights 分类
    if (group.aiInsightsCategories) {
      for (const category of group.aiInsightsCategories) {
        for (const catItem of category.items) {
          if (route.path === catItem.path) return group.id
        }
      }
    }
  }
  return null
})

function toggleSidebar() {
  const wasCollapsed = isCollapsed.value
  isCollapsed.value = !isCollapsed.value
  localStorage.setItem('sidebarCollapsed', String(isCollapsed.value))
  
  // 如果是从收起状态展开，自动展开当前菜单所在的分组，折叠其他分组
  if (wasCollapsed && !isCollapsed.value && currentGroup.value) {
    expandedGroups.value = [currentGroup.value]
  }
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

// 收起状态下显示分组弹出菜单
const hideTimeout = ref<ReturnType<typeof setTimeout> | null>(null)

const showGroupPopup = (groupId: string, event: MouseEvent) => {
  if (!isCollapsed.value) return
  // Clear any pending hide timeout
  if (hideTimeout.value) {
    clearTimeout(hideTimeout.value)
    hideTimeout.value = null
  }
  const target = event.currentTarget as HTMLElement
  const rect = target.getBoundingClientRect()
  popupPosition.value = { top: rect.top }
  activePopup.value = groupId
}

const hideGroupPopup = () => {
  // Delay hiding to allow mouse to move to popup
  hideTimeout.value = setTimeout(() => {
    activePopup.value = null
  }, 150)
}

const cancelHidePopup = () => {
  // Cancel hide when mouse enters popup
  if (hideTimeout.value) {
    clearTimeout(hideTimeout.value)
    hideTimeout.value = null
  }
}

// 获取分组图标（用于收起状态显示）
const getGroupIcon = (groupId: string) => {
  const iconMap: Record<string, any> = {
    'overview': HomeIcon,
    'data-protection': CloudArrowUpIcon,
    'resources': ServerIcon,
    'ai-insights': ChartBarIcon,
    'ops-monitor': ClipboardDocumentListIcon,
    'system': Cog6ToothIcon
  }
  return iconMap[groupId] || HomeIcon
}

// 图标名称到组件的映射（用于收藏栏）
const iconComponentMap: Record<string, any> = {
  'HomeIcon': HomeIcon,
  'ServerIcon': ServerIcon,
  'CloudArrowUpIcon': CloudArrowUpIcon,
  'ArrowUturnLeftIcon': ArrowUturnLeftIcon,
  'CircleStackIcon': CircleStackIcon,
  'ClockIcon': ClockIcon,
  'ClipboardDocumentListIcon': ClipboardDocumentListIcon,
  'Cog6ToothIcon': Cog6ToothIcon,
  'ComputerDesktopIcon': ComputerDesktopIcon,
  'BuildingOffice2Icon': BuildingOffice2Icon,
  'KeyIcon': KeyIcon,
  'UsersIcon': UsersIcon,
  'BellIcon': BellIcon,
  'ExclamationTriangleIcon': ExclamationTriangleIcon,
  'CloudIcon': CloudIcon,
  'ChartBarIcon': ChartBarIcon,
  'MagnifyingGlassIcon': MagnifyingGlassIcon,
  'ShieldCheckIcon': ShieldCheckIcon,
  'DocumentChartBarIcon': DocumentChartBarIcon,
  'FireIcon': FireIcon,
  'DocumentDuplicateIcon': DocumentDuplicateIcon,
  'ChatBubbleLeftRightIcon': ChatBubbleLeftRightIcon
}

const getIconComponent = (iconName: string) => {
  return iconComponentMap[iconName] || HomeIcon
}

// 收藏相关函数
const toggleFavorite = (item: { name: string; path: string; icon: any }, groupId: string) => {
  // 获取图标名称
  const iconName = Object.keys(iconComponentMap).find(key => iconComponentMap[key] === item.icon) || 'HomeIcon'
  
  const favoriteItem: FavoriteItem = {
    id: item.path,
    name: item.name,
    path: item.path,
    icon: iconName,
    groupId: groupId
  }
  
  favoritesStore.toggleFavorite(favoriteItem)
}

const isFavorite = (path: string): boolean => {
  return favoritesStore.isFavorite(path)
}

// 检查分组是否有当前激活项
const isGroupActive = (group: NavigationGroup) => {
  if (group.items.some(item => item.current || item.subItems?.some(sub => sub.current))) {
    return true
  }
  if (group.aiInsightsCategories?.some(cat => cat.items.some(item => item.current))) {
    return true
  }
  return false
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
      <div class="flex items-center justify-center h-16 px-4 border-b border-slate-200 dark:border-slate-700">
        <div class="flex items-center gap-2" v-if="!isCollapsed">
          <div class="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
            <CloudArrowUpIcon class="w-5 h-5 text-white" />
          </div>
          <span class="font-bold text-slate-900 dark:text-white text-lg">HyperFileLens</span>
        </div>
        <div v-else class="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
          <CloudArrowUpIcon class="w-5 h-5 text-white" />
        </div>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 px-2 py-4 space-y-1 overflow-y-auto h-[calc(100vh-8rem)]">
        <div v-for="group in navigationGroups" :key="group.id">
          <!-- Expanded state: show group header and items -->
          <div v-show="!isCollapsed">
            <!-- Group Header -->
            <div
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
            <div v-show="isGroupExpanded(group.id)" class="space-y-0.5">
              <div v-for="item in group.items" :key="item.path" class="relative group/item">
                <router-link
                  :to="item.path"
                  :class="[
                    'group flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors pr-10',
                    item.current
                      ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                      : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
                  ]"
                >
                  <component
                    :is="item.current ? item.iconSolid : item.icon"
                    :class="[
                      'w-4 h-4 flex-shrink-0',
                      item.current ? 'text-blue-500 dark:text-blue-400' : 'text-slate-400 group-hover:text-slate-500 dark:group-hover:text-slate-400'
                    ]"
                  />
                  <span>{{ item.name }}</span>
                </router-link>
                <!-- Favorite Button -->
                <button
                  @click.prevent="toggleFavorite(item, group.id)"
                  :class="[
                    'absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded opacity-0 group-hover/item:opacity-100 transition-opacity',
                    isFavorite(item.path) ? 'text-yellow-500 hover:text-yellow-600' : 'text-slate-400 hover:text-yellow-500'
                  ]"
                  :title="isFavorite(item.path) ? t('favorites.remove') : t('favorites.add')"
                >
                  <StarIcon v-if="isFavorite(item.path)" class="w-4 h-4 fill-current" />
                  <StarIcon v-else class="w-4 h-4" />
                </button>
                
                <!-- Sub Items -->
                <div v-if="item.subItems && item.subItems.length > 0" class="ml-4 mt-1 space-y-0.5">
                  <div v-for="subItem in item.subItems" :key="subItem.path" class="relative group/subitem">
                    <router-link
                      :to="subItem.path"
                      :class="[
                        'group flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors pr-8',
                        subItem.current
                          ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-medium'
                          : 'text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-slate-700 dark:hover:text-slate-300'
                      ]"
                    >
                      <span class="w-1.5 h-1.5 rounded-full" :class="subItem.current ? 'bg-blue-500' : 'bg-slate-300 dark:bg-slate-600'"></span>
                      {{ subItem.name }}
                    </router-link>
                    <!-- Favorite Button for Sub Item -->
                    <button
                      @click.prevent="toggleFavorite({ name: subItem.name, path: subItem.path, icon: subItem.icon }, group.id)"
                      :class="[
                        'absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded opacity-0 group-hover/subitem:opacity-100 transition-opacity',
                        isFavorite(subItem.path) ? 'text-yellow-500 hover:text-yellow-600' : 'text-slate-400 hover:text-yellow-500'
                      ]"
                      :title="isFavorite(subItem.path) ? t('favorites.remove') : t('favorites.add')"
                    >
                      <StarIcon v-if="isFavorite(subItem.path)" class="w-3.5 h-3.5 fill-current" />
                      <StarIcon v-else class="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- AI Insights Special Categories -->
            <div v-if="group.aiInsightsCategories" v-show="isGroupExpanded(group.id)" class="space-y-2">
              <div v-for="category in group.aiInsightsCategories" :key="category.name" class="mt-2">
                <!-- Category Label -->
                <div class="px-3 py-1.5 text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                  {{ category.name }}
                </div>
                <!-- Category Items (三级菜单) -->
                <div class="space-y-0.5 ml-4">
                  <div v-for="subItem in category.items" :key="subItem.path" class="relative group/aiitem">
                    <router-link
                      :to="subItem.path"
                      :class="[
                        'group flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors pr-8',
                        subItem.current
                          ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-medium'
                          : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-slate-700 dark:hover:text-slate-200'
                      ]"
                    >
                      <component
                        :is="subItem.current ? subItem.iconSolid : subItem.icon"
                        :class="[
                          'w-4 h-4 flex-shrink-0',
                          subItem.current ? 'text-blue-500 dark:text-blue-400' : 'text-slate-400 group-hover:text-slate-500 dark:group-hover:text-slate-400'
                        ]"
                      />
                      {{ subItem.name }}
                    </router-link>
                    <!-- Favorite Button for AI Insights Item -->
                    <button
                      @click.prevent="toggleFavorite({ name: subItem.name, path: subItem.path, icon: subItem.icon }, group.id)"
                      :class="[
                        'absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded opacity-0 group-hover/aiitem:opacity-100 transition-opacity',
                        isFavorite(subItem.path) ? 'text-yellow-500 hover:text-yellow-600' : 'text-slate-400 hover:text-yellow-500'
                      ]"
                      :title="isFavorite(subItem.path) ? t('favorites.remove') : t('favorites.add')"
                    >
                      <StarIcon v-if="isFavorite(subItem.path)" class="w-3.5 h-3.5 fill-current" />
                      <StarIcon v-else class="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Divider -->
            <div v-if="group.id !== 'system'" class="my-3 border-t border-slate-200 dark:border-slate-700"></div>
          </div>

          <!-- Collapsed state: show only group icon -->
          <div
            v-show="isCollapsed"
            @mouseenter="showGroupPopup(group.id, $event)"
            @mouseleave="hideGroupPopup"
            :class="[
              'relative flex items-center justify-center px-2 py-2 rounded-lg transition-colors cursor-pointer',
              isGroupActive(group) 
                ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400' 
                : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700'
            ]"
          >
            <component
              :is="getGroupIcon(group.id)"
              :class="[
                'w-5 h-5',
                isGroupActive(group) ? 'text-blue-500 dark:text-blue-400' : 'text-slate-400'
              ]"
            />
          </div>
        </div>
      </nav>

      <!-- Popup Menu for Collapsed Sidebar -->
      <Transition
        enter-active-class="transition ease-out duration-100"
        enter-from-class="opacity-0 translate-x-2"
        enter-to-class="opacity-100 translate-x-0"
        leave-active-class="transition ease-in duration-75"
        leave-from-class="opacity-100 translate-x-0"
        leave-to-class="opacity-0 translate-x-2"
      >
        <div
          v-if="activePopup && isCollapsed"
          class="fixed left-16 z-50 w-56 bg-white dark:bg-slate-800 rounded-lg shadow-xl border border-slate-200 dark:border-slate-700 py-2"
          :style="{ top: popupPosition.top + 'px' }"
          @mouseenter="cancelHidePopup"
          @mouseleave="hideGroupPopup"
        >
          <template v-for="group in navigationGroups" :key="group.id">
            <div v-if="group.id === activePopup">
              <!-- Popup Header -->
              <div class="px-3 py-2 text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider border-b border-slate-100 dark:border-slate-700">
                {{ group.title }}
              </div>
              
              <!-- Regular Items -->
              <div v-for="item in group.items" :key="item.path">
                <router-link
                  :to="item.path"
                  @click="hideGroupPopup"
                  :class="[
                    'group flex items-center gap-3 px-3 py-2 text-sm transition-colors',
                    item.current
                      ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                      : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
                  ]"
                >
                  <component
                    :is="item.current ? item.iconSolid : item.icon"
                    :class="[
                      'w-4 h-4 flex-shrink-0',
                      item.current ? 'text-blue-500 dark:text-blue-400' : 'text-slate-400 group-hover:text-slate-500'
                    ]"
                  />
                  {{ item.name }}
                </router-link>
                
                <!-- Sub Items in Popup -->
                <div v-if="item.subItems && item.subItems.length > 0" class="ml-6">
                  <router-link
                    v-for="subItem in item.subItems"
                    :key="subItem.path"
                    :to="subItem.path"
                    @click="hideGroupPopup"
                    :class="[
                      'group flex items-center gap-2 px-3 py-1.5 text-sm transition-colors',
                      subItem.current
                        ? 'text-blue-600 dark:text-blue-400 font-medium'
                        : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
                    ]"
                  >
                    <span class="w-1.5 h-1.5 rounded-full" :class="subItem.current ? 'bg-blue-500' : 'bg-slate-300 dark:bg-slate-600'"></span>
                    {{ subItem.name }}
                  </router-link>
                </div>
              </div>
              
              <!-- AI Insights Categories in Popup -->
              <div v-if="group.aiInsightsCategories">
                <div v-for="category in group.aiInsightsCategories" :key="category.name">
                  <div class="px-3 py-1.5 mt-2 text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                    {{ category.name }}
                  </div>
                  <router-link
                    v-for="subItem in category.items"
                    :key="subItem.path"
                    :to="subItem.path"
                    @click="hideGroupPopup"
                    :class="[
                      'group flex items-center gap-2.5 px-3 py-1.5 text-sm transition-colors',
                      subItem.current
                        ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                        : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
                    ]"
                  >
                    <component
                      :is="subItem.current ? subItem.iconSolid : subItem.icon"
                      :class="[
                        'w-4 h-4 flex-shrink-0',
                        subItem.current ? 'text-blue-500 dark:text-blue-400' : 'text-slate-400 group-hover:text-slate-500'
                      ]"
                    />
                    {{ subItem.name }}
                  </router-link>
                </div>
              </div>
            </div>
          </template>
        </div>
      </Transition>

      <!-- Collapse Button at Bottom -->
      <div class="absolute bottom-0 left-0 right-0 p-3 border-t border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800">
        <button
          @click="toggleSidebar"
          class="w-full flex items-center justify-center gap-2 p-2 rounded-lg text-slate-500 hover:text-slate-700 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-200 dark:hover:bg-slate-700 transition-colors"
        >
          <ChevronLeftIcon v-if="!isCollapsed" class="w-5 h-5" />
          <ChevronRightIcon v-else class="w-5 h-5" />
          <span v-if="!isCollapsed" class="text-sm">{{ $t('common.collapse') }}</span>
        </button>
      </div>
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
          <!-- Left side - empty or can show breadcrumbs -->
          <div class="flex items-center gap-4 flex-1">
            <!-- Reserved for future use -->
          </div>

          <!-- Center - Favorites Bar -->
          <div class="flex items-center justify-center flex-1">
            <div v-if="favoritesStore.favorites.length > 0" class="flex items-center gap-1">
              <div
                v-for="fav in favoritesStore.favorites"
                :key="fav.id"
                class="relative group/fav"
              >
                <router-link
                  :to="fav.path"
                  :class="[
                    'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors pr-8',
                    route.path === fav.path
                      ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                      : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
                  ]"
                >
                  <component
                    :is="getIconComponent(fav.icon)"
                    class="w-4 h-4"
                  />
                  <span>{{ fav.name }}</span>
                </router-link>
                <!-- Remove Favorite Button -->
                <button
                  @click.prevent="favoritesStore.removeFavorite(fav.id)"
                  class="absolute right-1 top-1/2 -translate-y-1/2 p-1 rounded-full opacity-0 group-hover/fav:opacity-100 transition-opacity text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30"
                  :title="$t('favorites.remove')"
                >
                  <XMarkIcon class="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
            <div v-else class="text-sm text-slate-400 dark:text-slate-500">
              {{ t('favorites.emptyHint') }}
            </div>
          </div>

          <!-- Right side - Theme & Language -->
          <div class="flex items-center gap-4 flex-1 justify-end">
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
