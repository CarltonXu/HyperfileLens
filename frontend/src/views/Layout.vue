<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useAppStore } from "@/stores/app";
import { useFavoritesStore } from "@/stores/favorites";
import type { FavoriteItem } from "@/stores/favorites";
import { useI18n } from "vue-i18n";
import BrandLogo from "@/components/BrandLogo.vue";
import ThemeSwitcher from "@/components/ThemeSwitcher.vue";
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
  Bars3Icon,
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
  // AI Insights 三级菜单图标
  ChartBarIcon,
  MagnifyingGlassIcon,
  ShieldCheckIcon,
  DocumentChartBarIcon,
  FireIcon,
  DocumentDuplicateIcon,
  ChatBubbleLeftRightIcon,
} from "@heroicons/vue/24/outline";
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
  StarIcon as StarIconSolid,
  // AI Insights 三级菜单图标
  ChartBarIcon as ChartBarIconSolid,
  MagnifyingGlassIcon as MagnifyingGlassIconSolid,
  ShieldCheckIcon as ShieldCheckIconSolid,
  DocumentChartBarIcon as DocumentChartBarIconSolid,
  FireIcon as FireIconSolid,
  DocumentDuplicateIcon as DocumentDuplicateIconSolid,
  ChatBubbleLeftRightIcon as ChatBubbleLeftRightIconSolid,
} from "@heroicons/vue/24/solid";

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const appStore = useAppStore();
const favoritesStore = useFavoritesStore();
const { t, locale } = useI18n();

const isCollapsed = ref(false);
const isUserMenuOpen = ref(false);
const isLangMenuOpen = ref(false);
const isFavoritesMenuOpen = ref(false);
const expandedGroups = ref<string[]>([]);
const favoriteGroupOrder = ref<string[]>([]);
const draggingFavoriteGroup = ref<string | null>(null);
const favoriteGroupDropTarget = ref<string | null>(null);

// 收起状态下的弹出菜单
const activePopup = ref<string | null>(null);
const popupPosition = ref({ top: 0 });

// 菜单项类型定义
interface MenuItem {
  name: string;
  path: string;
  icon: any;
  iconSolid?: any;
  current: boolean;
  requiresSuperuser?: boolean;
  requiresTenantAdmin?: boolean;
  subItems?: SubMenuItem[];
}

interface SubMenuItem {
  name: string;
  path: string;
  icon: any;
  iconSolid?: any;
  current: boolean;
}

// AI Insights 二级分类（固定标签，不可点击）
interface AIInsightsSubItem {
  name: string;
  path: string;
  current: boolean;
  icon: any;
  iconSolid?: any;
}

interface AIInsightsCategory {
  name: string; // 分类名称
  items: AIInsightsSubItem[]; // 三级菜单
}

interface NavigationGroup {
  id: string;
  title: string;
  items: MenuItem[];
  // AI Insights 特殊的三级菜单结构
  aiInsightsCategories?: AIInsightsCategory[];
}

function currentAIInsightQuery() {
  const query: Record<string, string> = {};
  for (const key of ["scope_type", "scope_id", "scope_name"]) {
    const value = route.query[key];
    if (typeof value === "string" && value) {
      query[key] = value;
    }
  }
  return query;
}

function aiInsightTo(path: string) {
  return { path, query: currentAIInsightQuery() };
}

// 欢迎弹窗
const showWelcome = ref(false);
const welcomeVisible = ref(false);

// 获取时间段问候语
const getGreeting = () => {
  const hour = new Date().getHours();
  if (hour >= 5 && hour < 12) {
    return {
      text: t("welcome.goodMorning"),
      icon: SunIcon,
      color: "text-amber-500",
    };
  } else if (hour >= 12 && hour < 18) {
    return {
      text: t("welcome.goodAfternoon"),
      icon: SunIcon,
      color: "text-orange-500",
    };
  } else {
    return {
      text: t("welcome.goodEvening"),
      icon: MoonIcon,
      color: "text-indigo-400",
    };
  }
};

// 显示欢迎弹窗
const showWelcomeToast = () => {
  showWelcome.value = true;
  setTimeout(() => {
    welcomeVisible.value = true;
  }, 50);
  setTimeout(() => {
    closeWelcome();
  }, 5000);
};

// 关闭欢迎弹窗
const closeWelcome = () => {
  welcomeVisible.value = false;
  setTimeout(() => {
    showWelcome.value = false;
  }, 300);
};

// 切换分组展开状态
const toggleGroup = (groupId: string) => {
  if (isCollapsed.value) return;
  const index = expandedGroups.value.indexOf(groupId);
  if (index > -1) {
    expandedGroups.value.splice(index, 1);
  } else {
    expandedGroups.value.push(groupId);
  }
};

// 检查分组是否展开
const isGroupExpanded = (groupId: string) => {
  return expandedGroups.value.includes(groupId);
};

// 导航分组
const navigationGroups = computed<NavigationGroup[]>(() => {
  const groups = [
    {
      id: "overview",
      title: t("navGroups.overview"),
      items: [
        {
          name: t("nav.dashboard"),
          path: "/",
          icon: HomeIcon,
          iconSolid: HomeIconSolid,
          current: route.path === "/",
        },
      ],
    },
    {
      id: "data-protection",
      title: t("navGroups.dataProtection"),
      items: [
        {
          name: t("nav.backupTasks"),
          path: "/backup-tasks",
          icon: CloudArrowUpIcon,
          iconSolid: CloudArrowUpIconSolid,
          current: route.path === "/backup-tasks",
        },
        {
          name: t("nav.recoveryTasks"),
          path: "/recovery-tasks",
          icon: ArrowUturnLeftIcon,
          iconSolid: ArrowUturnLeftIconSolid,
          current: route.path === "/recovery-tasks",
        },
        {
          name: t("nav.recoveryExports"),
          path: "/recovery-exports",
          icon: DocumentDuplicateIcon,
          iconSolid: DocumentDuplicateIconSolid,
          current: route.path === "/recovery-exports",
        },
        {
          name: t("nav.policies"),
          path: "/policies",
          icon: ClockIcon,
          iconSolid: ClockIconSolid,
          current: route.path === "/policies",
        },
      ],
    },
    {
      id: "resources",
      title: t("navGroups.resources"),
      items: [
        {
          name: t("nav.proxies"),
          path: "/proxies",
          icon: ServerIcon,
          iconSolid: ServerIconSolid,
          current: route.path.startsWith("/proxies"),
        },
        {
          name: t("nav.repository"),
          path: "/repository",
          icon: CircleStackIcon,
          iconSolid: CircleStackIconSolid,
          current: route.path === "/repository",
        },
        {
          name: t("nav.sourceResources"),
          path: "/source-resources",
          icon: ComputerDesktopIcon,
          iconSolid: ComputerDesktopIcon,
          current: route.path === "/source-resources",
        },
        {
          name: t("nav.gateways"),
          path: "/gateways",
          icon: CloudIcon,
          iconSolid: CloudIconSolid,
          current: route.path === "/gateways",
        },
      ],
    },
    {
      id: "ai-insights",
      title: t("navGroups.aiInsights"),
      items: [],
      // AI Insights 特殊的三级菜单结构
      aiInsightsCategories: [
        {
          name: t("aiInsights.menuCategories.discovery"),
          items: [
            {
              name: t("aiInsights.nav.overview"),
              path: "/ai-insights/overview",
              current:
                route.path === "/ai-insights/overview" ||
                route.path === "/ai-insights",
              icon: ChartBarIcon,
              iconSolid: ChartBarIconSolid,
            },
            {
              name: t("aiInsights.nav.smartSearch"),
              path: "/ai-insights/smart-search",
              current: route.path === "/ai-insights/smart-search",
              icon: MagnifyingGlassIcon,
              iconSolid: MagnifyingGlassIconSolid,
            },
          ],
        },
        {
          name: t("aiInsights.menuCategories.contentSecurity"),
          items: [
            {
              name: t("aiInsights.nav.sensitiveData"),
              path: "/ai-insights/sensitive-data",
              current: route.path === "/ai-insights/sensitive-data",
              icon: ShieldCheckIcon,
              iconSolid: ShieldCheckIconSolid,
            },
            {
              name: t("aiInsights.nav.contentProfile"),
              path: "/ai-insights/content-profiling",
              current: route.path === "/ai-insights/content-profiling",
              icon: DocumentChartBarIcon,
              iconSolid: DocumentChartBarIconSolid,
            },
          ],
        },
        {
          name: t("aiInsights.menuCategories.governance"),
          items: [
            {
              name: t("aiInsights.nav.dataHeatmap"),
              path: "/ai-insights/data-heatmap",
              current: route.path === "/ai-insights/data-heatmap",
              icon: FireIcon,
              iconSolid: FireIconSolid,
            },
            {
              name: t("aiInsights.nav.redundancy"),
              path: "/ai-insights/redundancy",
              current: route.path === "/ai-insights/redundancy",
              icon: DocumentDuplicateIcon,
              iconSolid: DocumentDuplicateIconSolid,
            },
          ],
        },
        {
          name: t("aiInsights.menuCategories.knowledge"),
          items: [
            {
              name: t("aiInsights.nav.aiChat"),
              path: "/ai-insights/ai-chat",
              current: route.path === "/ai-insights/ai-chat",
              icon: ChatBubbleLeftRightIcon,
              iconSolid: ChatBubbleLeftRightIconSolid,
            },
          ],
        },
      ],
    },
    {
      id: "operations",
      title: t("navGroups.operations"),
      items: [
        {
          name: t("nav.auditLog"),
          path: "/audit-log",
          icon: ClipboardDocumentListIcon,
          iconSolid: ClipboardDocumentListIconSolid,
          current: route.path === "/audit-log",
        },
        {
          name: t("nav.eventLog"),
          path: "/event-log",
          icon: BellIcon,
          iconSolid: BellIconSolid,
          current: route.path === "/event-log",
        },
        {
          name: t("nav.tenants"),
          path: "/tenants",
          icon: BuildingOffice2Icon,
          iconSolid: BuildingOffice2IconSolid,
          current: route.path === "/tenants",
          requiresSuperuser: true,
        },
        {
          name: t("nav.users"),
          path: "/users",
          icon: UsersIcon,
          iconSolid: UsersIconSolid,
          current: route.path === "/users",
          requiresTenantAdmin: true,
        },
      ],
    },
    {
      id: "monitor-alerts",
      title: t("navGroups.monitorAlerts"),
      items: [
        {
          name: t("alertsPage.tabs.monitor"),
          path: "/alerts/system-monitor",
          icon: ChartBarIcon,
          iconSolid: ChartBarIconSolid,
          current: route.path === "/alerts/system-monitor",
          requiresSuperuser: true,
        },
        {
          name: t("alertsCenter.nav.policies"),
          path: "/alerts/policies",
          icon: ExclamationTriangleIcon,
          iconSolid: ExclamationTriangleIconSolid,
          current: route.path.startsWith("/alerts/policies"),
        },
        {
          name: t("alertsCenter.nav.active"),
          path: "/alerts/active",
          icon: BellIcon,
          iconSolid: BellIconSolid,
          current: route.path === "/alerts/active",
        },
        {
          name: t("alertsCenter.nav.history"),
          path: "/alerts/history",
          icon: ClipboardDocumentListIcon,
          iconSolid: ClipboardDocumentListIconSolid,
          current: route.path === "/alerts/history",
        },
        {
          name: t("alertsCenter.nav.channels"),
          path: "/alerts/notification-channels",
          icon: BellIcon,
          iconSolid: BellIconSolid,
          current: route.path === "/alerts/notification-channels",
        },
        {
          name: t("alertsCenter.nav.notificationLogs"),
          path: "/alerts/notification-logs",
          icon: ClipboardDocumentListIcon,
          iconSolid: ClipboardDocumentListIconSolid,
          current: route.path === "/alerts/notification-logs",
        },
      ],
    },
    {
      id: "system",
      title: t("navGroups.system"),
      items: [
        {
          name: t("nav.licenses"),
          path: "/licenses",
          icon: KeyIcon,
          iconSolid: KeyIconSolid,
          current: route.path === "/licenses",
        },
        {
          name: t("nav.settings"),
          path: "/settings",
          icon: Cog6ToothIcon,
          iconSolid: Cog6ToothIconSolid,
          current: route.path === "/settings",
        },
      ],
    },
  ];

  // 过滤权限
  return (groups as NavigationGroup[])
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => {
        if (item.requiresSuperuser && !authStore.user?.is_superuser) {
          return false;
        }
        if (item.requiresTenantAdmin) {
          const isSuperuser = authStore.user?.is_superuser;
          const role = authStore.user?.tenant_role;
          if (!isSuperuser && role !== "admin") {
            return false;
          }
        }
        return true;
      }),
    }))
    .filter(
      (group) =>
        group.items.length > 0 ||
        (group.aiInsightsCategories && group.aiInsightsCategories.length > 0),
    );
});

// 获取当前路由所在的分组ID
const currentGroup = computed(() => {
  for (const group of navigationGroups.value) {
    // 检查普通菜单项
    for (const item of group.items) {
      if (item.current) return group.id;
      // 检查子菜单
      if (item.subItems) {
        for (const subItem of item.subItems) {
          if (route.path === subItem.path) return group.id;
        }
      }
    }
    // 检查 AI Insights 分类
    if (group.aiInsightsCategories) {
      for (const category of group.aiInsightsCategories) {
        for (const catItem of category.items) {
          if (route.path === catItem.path) return group.id;
        }
      }
    }
  }
  return null;
});

const favoriteGroupTitle = (groupId: string) =>
  navigationGroups.value.find((group) => group.id === groupId)?.title ||
  t("favorites.quickAccess");

const findNavigationFavorite = (favorite: FavoriteItem) => {
  for (const group of navigationGroups.value) {
    for (const item of group.items) {
      if (item.path === favorite.path) {
        return {
          ...favorite,
          name: item.name,
          icon: favorite.icon,
          groupId: group.id,
          groupTitle: group.title,
        };
      }

      const subItem = item.subItems?.find((sub) => sub.path === favorite.path);
      if (subItem) {
        return {
          ...favorite,
          name: subItem.name,
          icon: favorite.icon,
          groupId: group.id,
          groupTitle: group.title,
        };
      }
    }

    for (const category of group.aiInsightsCategories || []) {
      const subItem = category.items.find(
        (item) => item.path === favorite.path,
      );
      if (subItem) {
        return {
          ...favorite,
          name: subItem.name,
          icon: favorite.icon,
          groupId: group.id,
          groupTitle: category.name,
        };
      }
    }
  }

  return {
    ...favorite,
    groupTitle: favoriteGroupTitle(favorite.groupId),
  };
};

const localizedFavorites = computed(() =>
  favoritesStore.favorites.map(findNavigationFavorite),
);

const FAVORITE_GROUP_ORDER_KEY = "hyperfilelens_favorite_group_order";

const groupedFavorites = computed(() => {
  const groups: Array<{
    id: string;
    title: string;
    items: ReturnType<typeof findNavigationFavorite>[];
  }> = [];

  for (const favorite of localizedFavorites.value) {
    const groupId = favorite.groupId || "favorites";
    let group = groups.find((item) => item.id === groupId);
    if (!group) {
      group = {
        id: groupId,
        title: favorite.groupTitle || favoriteGroupTitle(groupId),
        items: [],
      };
      groups.push(group);
    }
    group.items.push(favorite);
  }

  const order = favoriteGroupOrder.value;
  return [...groups].sort((left, right) => {
    const leftIndex = order.indexOf(left.id);
    const rightIndex = order.indexOf(right.id);
    if (leftIndex === -1 && rightIndex === -1) return 0;
    if (leftIndex === -1) return 1;
    if (rightIndex === -1) return -1;
    return leftIndex - rightIndex;
  });
});

function loadFavoriteGroupOrder() {
  try {
    const stored = localStorage.getItem(FAVORITE_GROUP_ORDER_KEY);
    favoriteGroupOrder.value = stored ? JSON.parse(stored) : [];
  } catch {
    favoriteGroupOrder.value = [];
  }
}

function saveFavoriteGroupOrder(order: string[]) {
  favoriteGroupOrder.value = order;
  localStorage.setItem(FAVORITE_GROUP_ORDER_KEY, JSON.stringify(order));
}

function orderedFavoriteGroupIds() {
  return groupedFavorites.value.map((group) => group.id);
}

function moveFavoriteGroup(sourceGroupId: string, targetGroupId: string) {
  if (sourceGroupId === targetGroupId) return null;

  const currentOrder = orderedFavoriteGroupIds();
  const fromIndex = currentOrder.indexOf(sourceGroupId);
  const toIndex = currentOrder.indexOf(targetGroupId);
  if (fromIndex === -1 || toIndex === -1) return null;

  currentOrder.splice(fromIndex, 1);
  currentOrder.splice(toIndex, 0, sourceGroupId);
  favoriteGroupOrder.value = currentOrder;
  return currentOrder;
}

function startFavoriteGroupDrag(groupId: string, event: DragEvent) {
  draggingFavoriteGroup.value = groupId;
  favoriteGroupDropTarget.value = groupId;
  event.dataTransfer?.setData("text/plain", groupId);
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = "move";
    const dragBlock = (event.currentTarget as HTMLElement)?.closest(
      "[data-favorite-group]",
    ) as HTMLElement | null;
    if (dragBlock) {
      event.dataTransfer.setDragImage(dragBlock, 24, 18);
    }
  }
}

function previewFavoriteGroupDrop(targetGroupId: string, event: DragEvent) {
  const sourceGroupId = draggingFavoriteGroup.value;
  if (!sourceGroupId || sourceGroupId === targetGroupId) return;

  const currentOrder = orderedFavoriteGroupIds();
  const fromIndex = currentOrder.indexOf(sourceGroupId);
  const toIndex = currentOrder.indexOf(targetGroupId);
  if (fromIndex === -1 || toIndex === -1) return;

  const target = event.currentTarget as HTMLElement;
  const rect = target.getBoundingClientRect();
  const midpoint = rect.top + rect.height / 2;

  if (fromIndex < toIndex && event.clientY < midpoint) return;
  if (fromIndex > toIndex && event.clientY > midpoint) return;

  favoriteGroupDropTarget.value = targetGroupId;
  moveFavoriteGroup(sourceGroupId, targetGroupId);
}

function dropFavoriteGroup(targetGroupId: string) {
  const sourceGroupId = draggingFavoriteGroup.value;
  draggingFavoriteGroup.value = null;
  favoriteGroupDropTarget.value = null;
  if (!sourceGroupId) return;

  const order =
    moveFavoriteGroup(sourceGroupId, targetGroupId) ||
    orderedFavoriteGroupIds();
  saveFavoriteGroupOrder(order);
}

function endFavoriteGroupDrag() {
  if (draggingFavoriteGroup.value) {
    saveFavoriteGroupOrder(orderedFavoriteGroupIds());
  }
  draggingFavoriteGroup.value = null;
  favoriteGroupDropTarget.value = null;
}

function toggleSidebar() {
  const wasCollapsed = isCollapsed.value;
  isCollapsed.value = !isCollapsed.value;
  localStorage.setItem("sidebarCollapsed", String(isCollapsed.value));

  // 如果是从收起状态展开，自动展开当前菜单所在的分组，折叠其他分组
  if (wasCollapsed && !isCollapsed.value && currentGroup.value) {
    expandedGroups.value = [currentGroup.value];
  }
}

function toggleUserMenu() {
  isUserMenuOpen.value = !isUserMenuOpen.value;
  isLangMenuOpen.value = false;
  isFavoritesMenuOpen.value = false;
}

function toggleLangMenu() {
  isLangMenuOpen.value = !isLangMenuOpen.value;
  isUserMenuOpen.value = false;
  isFavoritesMenuOpen.value = false;
}

function toggleFavoritesMenu() {
  if (favoritesHideTimeout.value) {
    clearTimeout(favoritesHideTimeout.value);
    favoritesHideTimeout.value = null;
  }
  isFavoritesMenuOpen.value = !isFavoritesMenuOpen.value;
  isUserMenuOpen.value = false;
  isLangMenuOpen.value = false;
}

function cancelFavoritesHide() {
  if (favoritesHideTimeout.value) {
    clearTimeout(favoritesHideTimeout.value);
    favoritesHideTimeout.value = null;
  }
}

function hideFavoritesMenu() {
  favoritesHideTimeout.value = setTimeout(() => {
    isFavoritesMenuOpen.value = false;
    favoritesHideTimeout.value = null;
  }, 160);
}

async function handleLogout() {
  await authStore.logout();
  router.push("/login");
}

function openProfile() {
  isUserMenuOpen.value = false;
  router.push("/settings");
}

function setLocale(newLocale: string) {
  locale.value = newLocale;
  localStorage.setItem("locale", newLocale);
  isLangMenuOpen.value = false;
}

// 收起状态下显示分组弹出菜单
const hideTimeout = ref<ReturnType<typeof setTimeout> | null>(null);
const favoritesHideTimeout = ref<ReturnType<typeof setTimeout> | null>(null);

const showGroupPopup = (groupId: string, event: MouseEvent) => {
  if (!isCollapsed.value) return;
  // Clear any pending hide timeout
  if (hideTimeout.value) {
    clearTimeout(hideTimeout.value);
    hideTimeout.value = null;
  }
  const target = event.currentTarget as HTMLElement;
  const rect = target.getBoundingClientRect();
  popupPosition.value = { top: rect.top };
  activePopup.value = groupId;
};

const hideGroupPopup = () => {
  // Delay hiding to allow mouse to move to popup
  hideTimeout.value = setTimeout(() => {
    activePopup.value = null;
  }, 150);
};

const cancelHidePopup = () => {
  // Cancel hide when mouse enters popup
  if (hideTimeout.value) {
    clearTimeout(hideTimeout.value);
    hideTimeout.value = null;
  }
};

// 获取分组图标（用于收起状态显示）
const getGroupIcon = (groupId: string) => {
  const iconMap: Record<string, any> = {
    overview: HomeIcon,
    "data-protection": CloudArrowUpIcon,
    resources: ServerIcon,
    "ai-insights": ChartBarIcon,
    operations: ClipboardDocumentListIcon,
    system: Cog6ToothIcon,
  };
  return iconMap[groupId] || HomeIcon;
};

// 图标名称到组件的映射（用于收藏栏）
const iconComponentMap: Record<string, any> = {
  HomeIcon: HomeIcon,
  ServerIcon: ServerIcon,
  CloudArrowUpIcon: CloudArrowUpIcon,
  ArrowUturnLeftIcon: ArrowUturnLeftIcon,
  CircleStackIcon: CircleStackIcon,
  ClockIcon: ClockIcon,
  ClipboardDocumentListIcon: ClipboardDocumentListIcon,
  Cog6ToothIcon: Cog6ToothIcon,
  ComputerDesktopIcon: ComputerDesktopIcon,
  BuildingOffice2Icon: BuildingOffice2Icon,
  KeyIcon: KeyIcon,
  UsersIcon: UsersIcon,
  BellIcon: BellIcon,
  ExclamationTriangleIcon: ExclamationTriangleIcon,
  CloudIcon: CloudIcon,
  ChartBarIcon: ChartBarIcon,
  MagnifyingGlassIcon: MagnifyingGlassIcon,
  ShieldCheckIcon: ShieldCheckIcon,
  DocumentChartBarIcon: DocumentChartBarIcon,
  FireIcon: FireIcon,
  DocumentDuplicateIcon: DocumentDuplicateIcon,
  ChatBubbleLeftRightIcon: ChatBubbleLeftRightIcon,
};

const getIconComponent = (iconName: string) => {
  return iconComponentMap[iconName] || HomeIcon;
};

// 收藏相关函数
const toggleFavorite = (
  item: { name: string; path: string; icon: any },
  groupId: string,
) => {
  // 获取图标名称
  const iconName =
    Object.keys(iconComponentMap).find(
      (key) => iconComponentMap[key] === item.icon,
    ) || "HomeIcon";

  const favoriteItem: FavoriteItem = {
    id: item.path,
    name: item.name,
    path: item.path,
    icon: iconName,
    groupId: groupId,
  };

  // 如果已经收藏，直接移除
  if (favoritesStore.isFavorite(item.path)) {
    favoritesStore.removeFavorite(item.path);
    return;
  }

  // 检查是否可以添加收藏
  if (!favoritesStore.canAddFavorite) {
    appStore.warning(
      t("favorites.limitReached"),
      t("favorites.limitHint", { max: favoritesStore.maxFavorites }),
    );
    return;
  }

  favoritesStore.addFavorite(favoriteItem);
};

const isFavorite = (path: string): boolean => {
  return favoritesStore.isFavorite(path);
};

const navTourTargets: Record<string, string> = {
  "/": "nav-dashboard",
  "/proxies": "nav-proxies",
  "/gateways": "nav-gateways",
  "/source-resources": "nav-source-resources",
  "/repository": "nav-repository",
  "/policies": "nav-policies",
  "/backup-tasks": "nav-backup-tasks",
  "/ai-insights/overview": "nav-ai-insights-overview",
  "/recovery-tasks": "nav-recovery-tasks",
};

const getNavTourTarget = (path: string) => navTourTargets[path];

const findGroupIdForPath = (path?: string | null) => {
  if (!path) return null;
  for (const group of navigationGroups.value) {
    if (
      group.items.some((item) => {
        if (item.path === path) return true;
        if (item.path !== "/" && path.startsWith(`${item.path}/`)) return true;
        return item.subItems?.some((subItem) => subItem.path === path);
      })
    ) {
      return group.id;
    }
    if (
      group.aiInsightsCategories?.some((category) =>
        category.items.some((item) => item.path === path),
      )
    ) {
      return group.id;
    }
  }
  return null;
};

const expandGroupForPath = (path?: string | null) => {
  const groupId = findGroupIdForPath(path);
  if (groupId && !expandedGroups.value.includes(groupId)) {
    expandedGroups.value.push(groupId);
  }
};

const handlePrepareTourStep = (event: Event) => {
  const step = (event as CustomEvent<{ route?: string; selector?: string }>)
    .detail;
  isCollapsed.value = false;
  localStorage.setItem("sidebarCollapsed", "false");
  expandGroupForPath(step?.route);
};

// 检查分组是否有当前激活项
const isGroupActive = (group: NavigationGroup) => {
  if (
    group.items.some(
      (item) => item.current || item.subItems?.some((sub) => sub.current),
    )
  ) {
    return true;
  }
  if (
    group.aiInsightsCategories?.some((cat) =>
      cat.items.some((item) => item.current),
    )
  ) {
    return true;
  }
  return false;
};

// 处理欢迎弹窗
onMounted(() => {
  loadFavoriteGroupOrder();

  const collapsed = localStorage.getItem("sidebarCollapsed");
  if (collapsed === "true") {
    isCollapsed.value = true;
  }

  // 自动展开当前路由所在的分组
  if (currentGroup.value) {
    expandedGroups.value = [currentGroup.value];
  }

  window.addEventListener("hfl:prepare-tour-step", handlePrepareTourStep);

  // 显示欢迎弹窗
  if (sessionStorage.getItem("showWelcome") === "true") {
    sessionStorage.removeItem("showWelcome");
    setTimeout(() => {
      showWelcomeToast();
    }, 500);
  }
});

onUnmounted(() => {
  document.removeEventListener("click", () => {});
  window.removeEventListener("hfl:prepare-tour-step", handlePrepareTourStep);
});

watch(
  () => route.path,
  (path) => {
    expandGroupForPath(path);
  },
);
</script>

<template>
  <div class="min-h-screen app-background">
    <!-- Sidebar -->
    <aside
      :class="[
        'fixed left-0 top-16 z-40 h-[calc(100vh-4rem)] transition-all duration-300 ease-in-out',
        'bg-card border-r border-border',
        isCollapsed ? 'w-16' : 'w-64',
      ]"
    >
      <button
        type="button"
        :title="isCollapsed ? t('common.expand') : t('common.collapse')"
        :aria-label="isCollapsed ? t('common.expand') : t('common.collapse')"
        class="absolute -right-3 top-1/2 z-50 flex h-9 w-6 -translate-y-1/2 items-center justify-center rounded-full border border-border bg-card text-foreground-muted shadow-sm transition-all hover:border-blue-300 hover:bg-hover hover:text-blue-600 dark:hover:border-blue-700 dark:hover:text-blue-400"
        @click="toggleSidebar"
      >
        <ChevronLeftIcon v-if="!isCollapsed" class="h-4 w-4" />
        <ChevronRightIcon v-else class="h-4 w-4" />
      </button>

      <!-- Navigation -->
      <nav
        class="flex-1 px-2 py-4 space-y-1 overflow-y-auto h-[calc(100vh-4rem)]"
      >
        <div v-for="group in navigationGroups" :key="group.id">
          <!-- Expanded state: show group header and items -->
          <div v-show="!isCollapsed">
            <!-- Group Header -->
            <div
              @click="toggleGroup(group.id)"
              class="flex items-center justify-between px-3 py-2 text-xs font-semibold text-foreground-muted uppercase tracking-wider cursor-pointer hover:text-slate-500 dark:hover:text-slate-400"
            >
              <span>{{ group.title }}</span>
              <ChevronDownIcon
                :class="[
                  'w-4 h-4 transition-transform duration-200',
                  isGroupExpanded(group.id) ? 'rotate-0' : '-rotate-90',
                ]"
              />
            </div>

            <!-- Group Items -->
            <div v-show="isGroupExpanded(group.id)" class="ml-2 space-y-0.5">
              <div
                v-for="item in group.items"
                :key="item.path"
                class="relative group/item"
              >
                <router-link
                  :to="item.path"
                  :data-tour="getNavTourTarget(item.path)"
                  :class="[
                    'group flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors pr-10',
                    item.current
                      ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                      : 'hover:bg-hover',
                  ]"
                >
                  <component
                    :is="item.current ? item.iconSolid : item.icon"
                    :class="[
                      'w-4 h-4 flex-shrink-0',
                      item.current
                        ? 'text-blue-500 dark:text-blue-400'
                        : 'text-slate-400 group-hover:text-slate-500 dark:group-hover:text-slate-400',
                    ]"
                  />
                  <span>{{ item.name }}</span>
                </router-link>
                <!-- Favorite Button -->
                <button
                  @click.prevent="toggleFavorite(item, group.id)"
                  :class="[
                    'absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded transition-opacity',
                    isFavorite(item.path)
                      ? 'text-yellow-500 opacity-100 hover:text-yellow-600'
                      : 'text-slate-400 opacity-0 hover:text-yellow-500 group-hover/item:opacity-100',
                  ]"
                  :title="
                    isFavorite(item.path)
                      ? t('favorites.remove')
                      : t('favorites.add')
                  "
                >
                  <StarIcon
                    v-if="isFavorite(item.path)"
                    class="w-4 h-4 fill-current"
                  />
                  <StarIcon v-else class="w-4 h-4" />
                </button>

                <!-- Sub Items -->
                <div
                  v-if="item.subItems && item.subItems.length > 0"
                  class="ml-4 mt-1 space-y-0.5"
                >
                  <div
                    v-for="subItem in item.subItems"
                    :key="subItem.path"
                    class="relative group/subitem"
                    >
                    <router-link
                      :to="aiInsightTo(subItem.path)"
                      :data-tour="getNavTourTarget(subItem.path)"
                      :class="[
                        'group flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors pr-8',
                        subItem.current
                          ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-medium'
                          : 'text-foreground-secondary hover:bg-hover hover:text-slate-700 dark:hover:text-slate-300',
                      ]"
                    >
                      <span
                        class="w-1.5 h-1.5 rounded-full"
                        :class="
                          subItem.current
                            ? 'bg-blue-500'
                            : 'bg-slate-300 dark:bg-slate-600'
                        "
                      ></span>
                      {{ subItem.name }}
                    </router-link>
                    <!-- Favorite Button for Sub Item -->
                    <button
                      @click.prevent="
                        toggleFavorite(
                          {
                            name: subItem.name,
                            path: subItem.path,
                            icon: subItem.icon,
                          },
                          group.id,
                        )
                      "
                      :class="[
                        'absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded transition-opacity',
                        isFavorite(subItem.path)
                          ? 'text-yellow-500 opacity-100 hover:text-yellow-600'
                          : 'text-slate-400 opacity-0 hover:text-yellow-500 group-hover/subitem:opacity-100',
                      ]"
                      :title="
                        isFavorite(subItem.path)
                          ? t('favorites.remove')
                          : t('favorites.add')
                      "
                    >
                      <StarIcon
                        v-if="isFavorite(subItem.path)"
                        class="w-3.5 h-3.5 fill-current"
                      />
                      <StarIcon v-else class="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- AI Insights Special Categories -->
            <div
              v-if="group.aiInsightsCategories"
              v-show="isGroupExpanded(group.id)"
              class="ml-2 space-y-2"
            >
              <div
                v-for="category in group.aiInsightsCategories"
                :key="category.name"
                class="mt-2"
              >
                <!-- Category Label -->
                <div
                  class="px-3 py-1.5 text-xs font-semibold text-foreground-muted uppercase tracking-wider"
                >
                  {{ category.name }}
                </div>
                <!-- Category Items (三级菜单) -->
                <div class="ml-2 space-y-0.5">
                  <div
                    v-for="subItem in category.items"
                    :key="subItem.path"
                    class="relative group/aiitem"
                  >
                    <router-link
                      :to="subItem.path"
                      :data-tour="getNavTourTarget(subItem.path)"
                      :class="[
                        'group flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors pr-8',
                        subItem.current
                          ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-medium'
                          : 'text-foreground-secondary hover:bg-hover hover:text-slate-700 dark:hover:text-slate-200',
                      ]"
                    >
                      <component
                        :is="subItem.current ? subItem.iconSolid : subItem.icon"
                        :class="[
                          'w-4 h-4 flex-shrink-0',
                          subItem.current
                            ? 'text-blue-500 dark:text-blue-400'
                            : 'text-slate-400 group-hover:text-slate-500 dark:group-hover:text-slate-400',
                        ]"
                      />
                      {{ subItem.name }}
                    </router-link>
                    <!-- Favorite Button for AI Insights Item -->
                    <button
                      @click.prevent="
                        toggleFavorite(
                          {
                            name: subItem.name,
                            path: subItem.path,
                            icon: subItem.icon,
                          },
                          group.id,
                        )
                      "
                      :class="[
                        'absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded transition-opacity',
                        isFavorite(subItem.path)
                          ? 'text-yellow-500 opacity-100 hover:text-yellow-600'
                          : 'text-slate-400 opacity-0 hover:text-yellow-500 group-hover/aiitem:opacity-100',
                      ]"
                      :title="
                        isFavorite(subItem.path)
                          ? t('favorites.remove')
                          : t('favorites.add')
                      "
                    >
                      <StarIcon
                        v-if="isFavorite(subItem.path)"
                        class="w-3.5 h-3.5 fill-current"
                      />
                      <StarIcon v-else class="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Divider -->
            <div
              v-if="group.id !== 'system'"
              class="my-3 border-t border-border"
            ></div>
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
                : 'text-slate-500 hover:bg-hover',
            ]"
          >
            <component
              :is="getGroupIcon(group.id)"
              :class="[
                'w-5 h-5',
                isGroupActive(group)
                  ? 'text-blue-500 dark:text-blue-400'
                  : 'text-slate-400',
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
          class="fixed left-16 z-50 w-56 popover-surface rounded-lg shadow-xl border border-border py-2"
          :style="{ top: popupPosition.top + 'px' }"
          @mouseenter="cancelHidePopup"
          @mouseleave="hideGroupPopup"
        >
          <template v-for="group in navigationGroups" :key="group.id">
            <div v-if="group.id === activePopup">
              <!-- Popup Header -->
              <div
                class="px-3 py-2 text-xs font-semibold text-foreground-muted uppercase tracking-wider border-b border-border"
              >
                {{ group.title }}
              </div>

              <!-- Regular Items -->
              <div v-for="item in group.items" :key="item.path" class="ml-2">
                <div class="relative group/popup-item">
                  <router-link
                    :to="item.path"
                    @click="hideGroupPopup"
                    :class="[
                      'group flex items-center gap-3 px-3 py-2 pr-9 text-sm transition-colors',
                      item.current
                        ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                        : 'text-foreground-secondary hover:bg-hover',
                    ]"
                  >
                    <component
                      :is="item.current ? item.iconSolid : item.icon"
                      :class="[
                        'w-4 h-4 flex-shrink-0',
                        item.current
                          ? 'text-blue-500 dark:text-blue-400'
                          : 'text-slate-400 group-hover:text-slate-500',
                      ]"
                    />
                    <span class="min-w-0 flex-1 truncate">{{ item.name }}</span>
                  </router-link>
                  <button
                    @click.prevent.stop="toggleFavorite(item, group.id)"
                    :class="[
                      'absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 transition-opacity',
                      isFavorite(item.path)
                        ? 'text-yellow-500 opacity-100 hover:text-yellow-600'
                        : 'text-slate-400 opacity-0 hover:text-yellow-500 group-hover/popup-item:opacity-100',
                    ]"
                    :title="
                      isFavorite(item.path)
                        ? t('favorites.remove')
                        : t('favorites.add')
                    "
                  >
                    <StarIcon
                      v-if="isFavorite(item.path)"
                      class="h-3.5 w-3.5 fill-current"
                    />
                    <StarIcon v-else class="h-3.5 w-3.5" />
                  </button>
                </div>

                <!-- Sub Items in Popup -->
                <div
                  v-if="item.subItems && item.subItems.length > 0"
                  class="ml-6"
                >
                  <div
                    v-for="subItem in item.subItems"
                    :key="subItem.path"
                    class="relative group/popup-subitem"
                  >
                    <router-link
                      :to="aiInsightTo(subItem.path)"
                      @click="hideGroupPopup"
                      :class="[
                        'group flex items-center gap-2 px-3 py-1.5 pr-8 text-sm transition-colors',
                        subItem.current
                          ? 'text-blue-600 dark:text-blue-400 font-medium'
                          : 'text-foreground-secondary hover:text-slate-700 dark:hover:text-slate-300',
                      ]"
                    >
                      <span
                        class="w-1.5 h-1.5 rounded-full"
                        :class="
                          subItem.current
                            ? 'bg-blue-500'
                            : 'bg-slate-300 dark:bg-slate-600'
                        "
                      ></span>
                      <span class="min-w-0 flex-1 truncate">
                        {{ subItem.name }}
                      </span>
                    </router-link>
                    <button
                      @click.prevent.stop="
                        toggleFavorite(
                          {
                            name: subItem.name,
                            path: subItem.path,
                            icon: subItem.icon,
                          },
                          group.id,
                        )
                      "
                      :class="[
                        'absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 transition-opacity',
                        isFavorite(subItem.path)
                          ? 'text-yellow-500 opacity-100 hover:text-yellow-600'
                          : 'text-slate-400 opacity-0 hover:text-yellow-500 group-hover/popup-subitem:opacity-100',
                      ]"
                      :title="
                        isFavorite(subItem.path)
                          ? t('favorites.remove')
                          : t('favorites.add')
                      "
                    >
                      <StarIcon
                        v-if="isFavorite(subItem.path)"
                        class="h-3.5 w-3.5 fill-current"
                      />
                      <StarIcon v-else class="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              </div>

              <!-- AI Insights Categories in Popup -->
              <div v-if="group.aiInsightsCategories" class="ml-2">
                <div
                  v-for="category in group.aiInsightsCategories"
                  :key="category.name"
                >
                  <div
                    class="px-3 py-1.5 mt-2 text-xs font-semibold text-foreground-muted uppercase tracking-wider"
                  >
                    {{ category.name }}
                  </div>
                  <div
                    v-for="subItem in category.items"
                    :key="subItem.path"
                    class="relative ml-2 group/popup-aiitem"
                  >
                    <router-link
                      :to="subItem.path"
                      @click="hideGroupPopup"
                      :class="[
                        'group flex items-center gap-2.5 px-3 py-1.5 pr-9 text-sm transition-colors',
                        subItem.current
                          ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                          : 'text-foreground-secondary hover:bg-hover',
                      ]"
                    >
                      <component
                        :is="subItem.current ? subItem.iconSolid : subItem.icon"
                        :class="[
                          'w-4 h-4 flex-shrink-0',
                          subItem.current
                            ? 'text-blue-500 dark:text-blue-400'
                            : 'text-slate-400 group-hover:text-slate-500',
                        ]"
                      />
                      <span class="min-w-0 flex-1 truncate">
                        {{ subItem.name }}
                      </span>
                    </router-link>
                    <button
                      @click.prevent.stop="
                        toggleFavorite(
                          {
                            name: subItem.name,
                            path: subItem.path,
                            icon: subItem.icon,
                          },
                          group.id,
                        )
                      "
                      :class="[
                        'absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 transition-opacity',
                        isFavorite(subItem.path)
                          ? 'text-yellow-500 opacity-100 hover:text-yellow-600'
                          : 'text-slate-400 opacity-0 hover:text-yellow-500 group-hover/popup-aiitem:opacity-100',
                      ]"
                      :title="
                        isFavorite(subItem.path)
                          ? t('favorites.remove')
                          : t('favorites.add')
                      "
                    >
                      <StarIcon
                        v-if="isFavorite(subItem.path)"
                        class="h-3.5 w-3.5 fill-current"
                      />
                      <StarIcon v-else class="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>
      </Transition>
    </aside>

    <!-- Header -->
    <header class="fixed left-0 right-0 top-0 z-50 surface-card border-b border-border">
      <div class="flex h-16 min-w-0 items-center">
        <div
          :class="[
            'flex h-16 shrink-0 items-center justify-center border-r border-border px-4 transition-all duration-300',
            isCollapsed ? 'w-16' : 'w-64',
          ]"
        >
          <BrandLogo v-if="!isCollapsed" variant="full" size="sm" />
          <BrandLogo v-else variant="mark" size="sm" />
        </div>

        <div class="relative flex h-16 min-w-0 flex-1 items-center justify-between px-6">
          <!-- Left side - empty or can show breadcrumbs -->
          <div class="hidden min-w-0 items-center gap-4 flex-1 lg:flex">
            <!-- Reserved for future use -->
          </div>

          <!-- Center - Favorites Bar -->
          <div
            class="absolute left-1/2 top-1/2 z-10 flex min-w-0 -translate-x-1/2 -translate-y-1/2 items-center justify-center"
            @mouseenter="cancelFavoritesHide"
            @mouseleave="hideFavoritesMenu"
          >
            <button
              type="button"
              class="inline-flex items-center gap-2 rounded-lg border border-border bg-background/70 px-3 py-1.5 text-sm text-foreground-secondary shadow-sm transition-colors hover:bg-hover hover:text-foreground"
              :title="t('favorites.quickAccess')"
              @click="toggleFavoritesMenu"
            >
              <StarIconSolid class="h-4 w-4 text-yellow-500" />
              <span class="font-medium">{{ t("favorites.quickAccess") }}</span>
              <span
                class="rounded-full bg-background-secondary px-1.5 py-0.5 text-[11px] font-semibold text-foreground-muted"
              >
                {{ favoritesStore.favorites.length }}
              </span>
            </button>
            <Transition
              enter-active-class="transition ease-out duration-100"
              enter-from-class="opacity-0 translate-y-1 scale-95"
              enter-to-class="opacity-100 translate-y-0 scale-100"
              leave-active-class="transition ease-in duration-75"
              leave-from-class="opacity-100 translate-y-0 scale-100"
              leave-to-class="opacity-0 translate-y-1 scale-95"
            >
              <div
                v-if="isFavoritesMenuOpen"
                class="absolute left-1/2 top-full z-50 mt-3 w-[560px] -translate-x-1/2 rounded-xl border border-border popover-surface p-3 shadow-xl"
              >
                <div
                  class="mb-3 flex items-start justify-between gap-4 border-b border-border pb-3"
                >
                  <div class="min-w-0">
                    <p class="text-sm font-semibold text-foreground">
                      {{ t("favorites.quickAccess") }}
                    </p>
                    <p class="mt-0.5 text-xs text-foreground-secondary">
                      {{ t("favorites.quickAccessHint") }}
                    </p>
                  </div>
                  <span
                    class="shrink-0 rounded-full bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
                  >
                    {{ favoritesStore.favorites.length }}
                  </span>
                </div>

                <div
                  v-if="localizedFavorites.length > 0"
                  class="max-h-[420px] space-y-0 overflow-y-auto pr-1"
                >
                  <TransitionGroup
                    tag="div"
                    class="space-y-0"
                    move-class="transition-transform duration-300 ease-out"
                    enter-active-class="transition duration-150 ease-out"
                    enter-from-class="opacity-0 -translate-y-1"
                    enter-to-class="opacity-100 translate-y-0"
                    leave-active-class="transition duration-100 ease-in"
                    leave-from-class="opacity-100"
                    leave-to-class="opacity-0"
                  >
                    <section
                      v-for="group in groupedFavorites"
                      :key="group.id"
                      :data-favorite-group="group.id"
                      :class="[
                        'space-y-2 rounded-xl border border-transparent p-2 transition-all duration-200',
                        draggingFavoriteGroup === group.id
                          ? 'scale-[0.985] border-blue-300 bg-blue-50/40 opacity-85 shadow-md ring-1 ring-blue-400/30 dark:border-blue-800 dark:bg-blue-900/15'
                          : '',
                        favoriteGroupDropTarget === group.id &&
                        draggingFavoriteGroup !== group.id
                          ? 'border-blue-300 bg-blue-50/35 shadow-sm ring-1 ring-blue-300/25 dark:border-blue-800 dark:bg-blue-900/15'
                          : '',
                      ]"
                      @dragover.prevent="
                        previewFavoriteGroupDrop(group.id, $event)
                      "
                      @drop.prevent="dropFavoriteGroup(group.id)"
                    >
                      <div class="flex items-center gap-2 px-1">
                        <button
                          type="button"
                          draggable="true"
                          class="shrink-0 cursor-grab rounded-md border border-transparent p-1 text-foreground-muted transition-colors hover:border-border hover:bg-hover hover:text-foreground active:cursor-grabbing"
                          :title="t('favorites.dragGroup')"
                          @dragstart="startFavoriteGroupDrag(group.id, $event)"
                          @dragend="endFavoriteGroupDrag"
                        >
                          <Bars3Icon class="h-3.5 w-3.5" />
                        </button>
                        <p
                          class="text-[11px] font-semibold uppercase tracking-wider text-foreground-muted"
                        >
                          {{ group.title }}
                        </p>
                        <span
                          class="rounded-full bg-background-secondary px-1.5 py-0.5 text-[10px] font-medium text-foreground-muted"
                        >
                          {{ group.items.length }}
                        </span>
                        <span class="h-px flex-1 bg-border" />
                      </div>
                      <div class="grid grid-cols-2 gap-1">
                        <router-link
                          v-for="fav in group.items"
                          :key="fav.id"
                          :to="fav.path"
                          :class="[
                            'group/fav-card relative flex min-w-0 items-center gap-3 rounded-lg px-2.5 py-2 pr-10 text-left transition-colors',
                            route.path === fav.path
                              ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400'
                              : 'text-foreground-secondary hover:bg-hover hover:text-foreground',
                          ]"
                          @click="isFavoritesMenuOpen = false"
                        >
                          <div
                            :class="[
                              'flex h-7 w-7 shrink-0 items-center justify-center rounded-md',
                              route.path === fav.path
                                ? 'bg-blue-100 text-blue-600 dark:bg-blue-900/50 dark:text-blue-300'
                                : 'bg-background-secondary text-slate-500 dark:text-slate-400 group-hover/fav-card:text-slate-600 dark:group-hover/fav-card:text-slate-200',
                            ]"
                          >
                            <component
                              :is="getIconComponent(fav.icon)"
                              class="h-4 w-4"
                            />
                          </div>
                          <div class="min-w-0 flex-1 py-0.5">
                            <p
                              class="whitespace-normal text-sm font-medium leading-5"
                            >
                              {{ fav.name }}
                            </p>
                          </div>
                          <button
                            type="button"
                            class="absolute right-2 top-1/2 -translate-y-1/2 rounded-full p-1 text-yellow-500 opacity-100 transition-opacity hover:bg-background-secondary"
                            :title="$t('favorites.remove')"
                            @click.prevent.stop="
                              favoritesStore.removeFavorite(fav.id)
                            "
                          >
                            <StarIconSolid class="h-3.5 w-3.5" />
                          </button>
                        </router-link>
                      </div>
                    </section>
                  </TransitionGroup>
                </div>

                <div
                  v-else
                  class="rounded-lg border border-dashed border-border bg-background/40 px-4 py-8 text-center"
                >
                  <StarIcon class="mx-auto h-7 w-7 text-foreground-muted" />
                  <p class="mt-2 text-sm font-medium text-foreground">
                    {{ t("favorites.emptyTitle") }}
                  </p>
                  <p class="mt-1 text-xs text-foreground-secondary">
                    {{ t("favorites.emptyHint") }}
                  </p>
                </div>
              </div>
            </Transition>
          </div>

          <!-- Right side - Theme & Language -->
          <div
            class="relative z-20 flex min-w-0 shrink-0 items-center gap-4 justify-end"
          >
            <!-- Theme Switcher -->
            <ThemeSwitcher />

            <!-- Language Switcher -->
            <div class="relative">
              <button
                @click="toggleLangMenu"
                class="flex items-center gap-2 p-2 rounded-lg text-slate-500 hover:text-slate-700 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-200"
              >
                <LanguageIcon class="w-5 h-5" />
                <span class="text-sm">{{
                  locale === "zh-CN" ? "中文" : "EN"
                }}</span>
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
                  class="absolute right-0 mt-2 w-32 popover-surface rounded-lg shadow-lg border border-border py-1"
                >
                  <button
                    @click="setLocale('zh-CN')"
                    :class="[
                      'w-full px-4 py-2 text-left text-sm hover:bg-hover',
                      locale === 'zh-CN'
                        ? 'text-blue-600 dark:text-blue-400 font-medium'
                        : 'text-foreground-secondary',
                    ]"
                  >
                    中文
                  </button>
                  <button
                    @click="setLocale('en')"
                    :class="[
                      'w-full px-4 py-2 text-left text-sm hover:bg-hover',
                      locale === 'en'
                        ? 'text-blue-600 dark:text-blue-400 font-medium'
                        : 'text-foreground-secondary',
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
                class="flex items-center gap-2 p-2 rounded-lg text-slate-500 hover:text-slate-700 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-200"
              >
                <UserCircleIcon class="w-6 h-6" />
                <span class="text-sm font-medium">{{
                  authStore.user?.full_name || authStore.user?.email
                }}</span>
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
                  class="absolute right-0 mt-2 w-48 popover-surface rounded-lg shadow-lg border border-border py-1"
                >
                  <button
                    @click="openProfile"
                    class="w-full px-4 py-2 text-left text-sm text-foreground-secondary hover:bg-hover flex items-center gap-2"
                  >
                    <Cog6ToothIcon class="w-4 h-4" />
                    {{ t("nav.settings") }}
                  </button>
                  <hr class="my-1 border-border" />
                  <button
                    @click="handleLogout"
                    class="w-full px-4 py-2 text-left text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-2"
                  >
                    <ArrowRightStartOnRectangleIcon class="w-4 h-4" />
                    {{ t("common.logout") }}
                  </button>
                </div>
              </Transition>
            </div>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <div
      :class="['pt-16 transition-all duration-300', isCollapsed ? 'ml-16' : 'ml-64']"
    >
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
        class="fixed top-20 right-6 z-50 w-80 popover-surface rounded-xl shadow-2xl border border-border overflow-hidden"
      >
        <div class="bg-gradient-to-r from-blue-500 to-purple-600 px-4 py-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <component
                :is="getGreeting().icon"
                :class="['w-5 h-5', getGreeting().color]"
              />
              <span class="text-white font-medium">{{
                getGreeting().text
              }}</span>
            </div>
            <button
              @click="closeWelcome"
              class="text-white/80 hover:text-white"
            >
              <svg
                class="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>
        <div class="px-4 py-3">
          <div class="flex items-center gap-3">
            <div
              class="w-10 h-10 bg-gradient-to-br from-blue-400 to-purple-500 rounded-full flex items-center justify-center text-white font-bold text-lg"
            >
              {{
                (authStore.user?.full_name ||
                  authStore.user?.email ||
                  "U")[0].toUpperCase()
              }}
            </div>
            <div>
              <div class="font-medium text-foreground">
                {{ authStore.user?.full_name || authStore.user?.email }}
              </div>
              <div class="text-sm text-foreground-secondary">
                {{ t("welcome.subtitle") }}
              </div>
            </div>
          </div>
        </div>
        <div
          class="bg-background-secondary px-4 py-2 text-xs text-foreground-muted text-center"
        >
          HyperFileLens · {{ t("welcome.subtitle") }}
        </div>
      </div>
    </Transition>
  </div>
</template>
