import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// Lazy load views
const Dashboard = () => import('@/views/Dashboard.vue')
const Login = () => import('@/views/Login.vue')
const Proxies = () => import('@/views/Proxies.vue')
const ProxyDetail = () => import('@/views/ProxyDetail.vue')
const BackupTasks = () => import('@/views/BackupTasks.vue')
const RecoveryTasks = () => import('@/views/RecoveryTasks.vue')
const Repository = () => import('@/views/Repository.vue')
const SourceResources = () => import('@/views/SourceResources.vue')
const Policies = () => import('@/views/Policies.vue')
const AIQuery = () => import('@/views/AIQuery.vue')
const AuditLog = () => import('@/views/AuditLog.vue')
const Settings = () => import('@/views/Settings.vue')
const Layout = () => import('@/views/Layout.vue')

// Route types
declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    requiresAuth?: boolean
    layout?: 'default' | 'auth'
  }
}

// Routes
const routes: RouteRecordRaw[] = [
  // Auth routes
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: {
      title: 'Login',
      layout: 'auth',
      requiresAuth: false
    }
  },

  // Main routes with layout
  {
    path: '/',
    component: Layout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: Dashboard,
        meta: { title: 'Dashboard' }
      },
      {
        path: 'proxies',
        name: 'Proxies',
        component: Proxies,
        meta: { title: 'Proxy Management' }
      },
      {
        path: 'proxies/:id',
        name: 'ProxyDetail',
        component: ProxyDetail,
        meta: { title: 'Proxy Details' }
      },
      {
        path: 'backup-tasks',
        name: 'BackupTasks',
        component: BackupTasks,
        meta: { title: 'Backup Tasks' }
      },
      {
        path: 'recovery-tasks',
        name: 'RecoveryTasks',
        component: RecoveryTasks,
        meta: { title: 'Recovery Tasks' }
      },
      {
        path: 'repository',
        name: 'Repository',
        component: Repository,
        meta: { title: 'Backup Repository' }
      },
      {
        path: 'source-resources',
        name: 'SourceResources',
        component: SourceResources,
        meta: { title: 'Source Resources' }
      },
      {
        path: 'policies',
        name: 'Policies',
        component: Policies,
        meta: { title: 'Backup Policies' }
      },
      {
        path: 'ai-query',
        name: 'AIQuery',
        component: AIQuery,
        meta: { title: 'AI File Intelligence' }
      },
      {
        path: 'audit-log',
        name: 'AuditLog',
        component: AuditLog,
        meta: { title: 'Audit Log' }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: Settings,
        meta: { title: 'Settings' }
      },

      // Redirect old nodes path to proxies
      {
        path: 'nodes',
        redirect: '/proxies'
      },
      {
        path: 'nodes/:id',
        redirect: (to) => ({ path: `/proxies/${to.params.id}` })
      }
    ]
  },

  // Catch all
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

// Create router
const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(_to, _from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    }
    return { top: 0 }
  }
})

// Navigation guard
router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()

  // Check if route requires authentication
  if (to.meta.requiresAuth !== false && !authStore.isAuthenticated) {
    // Try to restore session
    if (authStore.token) {
      try {
        await authStore.fetchUser()
        next()
        return
      } catch {
        // Token invalid, redirect to login
        next({ name: 'Login', query: { redirect: to.fullPath } })
        return
      }
    }
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  }

  // If authenticated and trying to access login, redirect to dashboard
  if (to.name === 'Login' && authStore.isAuthenticated) {
    next({ name: 'Dashboard' })
    return
  }

  next()
})

export default router
