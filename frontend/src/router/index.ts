import {
  createRouter,
  createWebHistory,
  type RouteRecordRaw,
} from "vue-router";
import { useAuthStore } from "@/stores/auth";

// Lazy load views
const Dashboard = () => import("@/views/Dashboard.vue");
const Login = () => import("@/views/Login.vue");
const Proxies = () => import("@/views/Proxies.vue");
const BackupTasks = () => import("@/views/BackupTasks.vue");
const RecoveryTasks = () => import("@/views/RecoveryTasks.vue");
const RecoveryExports = () => import("@/views/RecoveryExports.vue");
const SharedRecoveryExport = () => import("@/views/SharedRecoveryExport.vue");
const SnapshotInsights = () => import("@/views/SnapshotInsights.vue");
const Repository = () => import("@/views/Repository.vue");
const SourceResources = () => import("@/views/SourceResources.vue");
const Policies = () => import("@/views/Policies.vue");
const AIInsights = () => import("@/views/AIInsights.vue");
const AuditLog = () => import("@/views/AuditLog.vue");
const EventLog = () => import("@/views/EventLog.vue");
const SystemMonitor = () => import("@/views/SystemMonitor.vue");
const AlertPolicies = () => import("@/views/alerts/AlertPolicies.vue");
const AlertPolicyEdit = () => import("@/views/alerts/AlertPolicyEdit.vue");
const ActiveAlerts = () => import("@/views/alerts/ActiveAlerts.vue");
const AlertHistory = () => import("@/views/alerts/AlertHistory.vue");
const NotificationChannels = () =>
  import("@/views/alerts/NotificationChannels.vue");
const NotificationLogs = () => import("@/views/alerts/NotificationLogs.vue");
const Settings = () => import("@/views/Settings.vue");
const Layout = () => import("@/views/Layout.vue");
const Tenants = () => import("@/views/Tenants.vue");
const Users = () => import("@/views/Users.vue");
const Licenses = () => import("@/views/Licenses.vue");
const Gateways = () => import("@/views/Gateways.vue");
const Register = () => import("@/views/Register.vue");
const ForgotPassword = () => import("@/views/ForgotPassword.vue");
const AcceptInvitation = () => import("@/views/AcceptInvitation.vue");

// Route types
declare module "vue-router" {
  interface RouteMeta {
    title?: string;
    requiresAuth?: boolean;
    layout?: "default" | "auth";
    requiresSuperuser?: boolean;
  }
}

// Routes
const routes: RouteRecordRaw[] = [
  // Auth routes
  {
    path: "/login",
    name: "Login",
    component: Login,
    meta: {
      title: "Login",
      layout: "auth",
      requiresAuth: false,
    },
  },
  {
    path: "/register",
    name: "Register",
    component: Register,
    meta: {
      title: "Register",
      layout: "auth",
      requiresAuth: false,
    },
  },
  {
    path: "/forgot-password",
    name: "ForgotPassword",
    component: ForgotPassword,
    meta: {
      title: "Forgot Password",
      layout: "auth",
      requiresAuth: false,
    },
  },
  {
    path: "/accept-invitation",
    name: "AcceptInvitation",
    component: AcceptInvitation,
    meta: {
      title: "Accept Invitation",
      layout: "auth",
      requiresAuth: false,
    },
  },
  {
    path: "/shared/recovery-export/:id",
    name: "SharedRecoveryExport",
    component: SharedRecoveryExport,
    meta: {
      title: "Shared Recovery Export",
      requiresAuth: false,
    },
  },

  // Main routes with layout
  {
    path: "/",
    component: Layout,
    meta: { requiresAuth: true },
    children: [
      {
        path: "",
        name: "Dashboard",
        component: Dashboard,
        meta: { title: "Dashboard" },
      },
      {
        path: "proxies",
        name: "Proxies",
        component: Proxies,
        meta: { title: "Proxy Management" },
      },
      {
        path: "proxies/:id",
        redirect: (to) => ({
          path: "/proxies",
          query: { detail: String(to.params.id) },
        }),
      },
      {
        path: "backup-tasks",
        name: "BackupTasks",
        component: BackupTasks,
        meta: { title: "Backup Tasks" },
      },
      {
        path: "snapshots/:snapshotId/insights",
        name: "SnapshotInsights",
        component: SnapshotInsights,
        meta: { title: "Snapshot Insights" },
      },
      {
        path: "recovery-tasks",
        name: "RecoveryTasks",
        component: RecoveryTasks,
        meta: { title: "Recovery Tasks" },
      },
      {
        path: "recovery-exports",
        name: "RecoveryExports",
        component: RecoveryExports,
        meta: { title: "Recovery Exports" },
      },
      {
        path: "repository",
        name: "Repository",
        component: Repository,
        meta: { title: "Backup Repository" },
      },
      {
        path: "source-resources",
        name: "SourceResources",
        component: SourceResources,
        meta: { title: "Source Resources" },
      },
      {
        path: "gateways",
        name: "Gateways",
        component: Gateways,
        meta: { title: "Gateways" },
      },
      {
        path: "policies",
        name: "Policies",
        component: Policies,
        meta: { title: "Backup Policies" },
      },
      {
        path: "ai-insights",
        name: "AIInsights",
        component: AIInsights,
        meta: { title: "AI Insights" },
        children: [
          {
            path: "overview",
            name: "AIInsightsOverview",
            component: AIInsights,
            meta: { title: "Insight Overview", tab: "overview" },
          },
          {
            path: "",
            redirect: "/ai-insights/overview",
          },
          {
            path: "smart-search",
            name: "AIInsightsSearch",
            component: AIInsights,
            meta: { title: "Smart Search", tab: "search" },
          },
          {
            path: "sensitive-data",
            name: "AIInsightsSensitive",
            component: AIInsights,
            meta: { title: "Sensitive Data", tab: "sensitive" },
          },
          {
            path: "content-profiling",
            name: "AIInsightsProfile",
            component: AIInsights,
            meta: { title: "Content Profile", tab: "profile" },
          },
          {
            path: "data-heatmap",
            name: "AIInsightsHeatmap",
            component: AIInsights,
            meta: { title: "Data Heatmap", tab: "heatmap" },
          },
          {
            path: "redundancy",
            name: "AIInsightsRedundancy",
            component: AIInsights,
            meta: { title: "Redundancy Analysis", tab: "redundancy" },
          },
          {
            path: "ai-chat",
            name: "AIInsightsChat",
            component: AIInsights,
            meta: { title: "AI Chat", tab: "chat" },
          },
        ],
      },
      {
        path: "audit-log",
        name: "AuditLog",
        component: AuditLog,
        meta: { title: "Audit Log" },
      },
      {
        path: "event-log",
        name: "EventLog",
        component: EventLog,
        meta: { title: "Task Management" },
      },
      {
        path: "alerts",
        redirect: "/alerts/policies",
      },
      {
        path: "alerts/system-monitor",
        name: "SystemMonitor",
        component: SystemMonitor,
        meta: { title: "System Monitor", requiresSuperuser: true },
      },
      {
        path: "alerts/policies",
        name: "AlertPolicies",
        component: AlertPolicies,
        meta: { title: "Alert Policies" },
      },
      {
        path: "alerts/policies/:id/edit",
        name: "AlertPolicyEdit",
        component: AlertPolicyEdit,
        meta: { title: "Edit Alert Policy" },
      },
      {
        path: "alerts/active",
        name: "ActiveAlerts",
        component: ActiveAlerts,
        meta: { title: "Active Alerts" },
      },
      {
        path: "alerts/history",
        name: "AlertHistory",
        component: AlertHistory,
        meta: { title: "Alert History" },
      },
      {
        path: "alerts/notification-channels",
        name: "NotificationChannels",
        component: NotificationChannels,
        meta: { title: "Notification Channels" },
      },
      {
        path: "alerts/notification-logs",
        name: "NotificationLogs",
        component: NotificationLogs,
        meta: { title: "Notification Logs" },
      },
      {
        path: "settings",
        name: "Settings",
        component: Settings,
        meta: { title: "Settings" },
      },
      {
        path: "settings/smtp",
        name: "SettingsSMTP",
        redirect: "/settings?tab=email",
        meta: { title: "SMTP Settings", requiresSuperuser: true },
      },
      {
        path: "tenants",
        name: "Tenants",
        component: Tenants,
        meta: { title: "Tenant Management", requiresSuperuser: true },
      },
      {
        path: "users",
        name: "Users",
        component: Users,
        meta: { title: "User Management", requiresTenantAdmin: true },
      },
      {
        path: "licenses",
        name: "Licenses",
        component: Licenses,
        meta: { title: "License Management" },
      },

      // Redirect old nodes path to proxies
      {
        path: "nodes",
        redirect: "/proxies",
      },
      {
        path: "nodes/:id",
        redirect: (to) => ({
          path: "/proxies",
          query: { detail: String(to.params.id) },
        }),
      },
    ],
  },

  // Catch all
  {
    path: "/:pathMatch(.*)*",
    redirect: "/",
  },
];

// Create router
const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(_to, _from, savedPosition) {
    if (savedPosition) {
      return savedPosition;
    }
    return { top: 0 };
  },
});

// Navigation guard
router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore();
  const isAuthRoute = [
    "Login",
    "Register",
    "ForgotPassword",
    "AcceptInvitation",
  ].includes(String(to.name));

  if (isAuthRoute) {
    if (authStore.isAuthenticated && to.name !== "AcceptInvitation") {
      next({ name: "Dashboard" });
      return;
    }
    if (authStore.token && !authStore.user) {
      localStorage.removeItem("token");
      authStore.token = null;
    }
  }

  // Check if route requires authentication
  if (to.meta.requiresAuth !== false && !authStore.isAuthenticated) {
    // Try to restore session
    if (authStore.token) {
      try {
        await authStore.fetchUser();
        // Check superuser permission after fetching user
        if (to.meta.requiresSuperuser && !authStore.user?.is_superuser) {
          next({ name: "Dashboard" });
          return;
        }
        next();
        return;
      } catch {
        // Token invalid, redirect to login
        next({ name: "Login", query: { redirect: to.fullPath } });
        return;
      }
    }
    next({ name: "Login", query: { redirect: to.fullPath } });
    return;
  }

  // Check superuser permission for authenticated users
  if (to.meta.requiresSuperuser && !authStore.user?.is_superuser) {
    next({ name: "Dashboard" });
    return;
  }

  // Check tenant admin permission (superuser or tenant admin)
  if (to.meta.requiresTenantAdmin) {
    const isSuperuser = authStore.user?.is_superuser;
    const role = authStore.user?.tenant_role;
    if (!isSuperuser && role !== "admin") {
      next({ name: "Dashboard" });
      return;
    }
  }
  next();
});

export default router;
