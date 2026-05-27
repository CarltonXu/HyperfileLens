<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { RouterView, useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import { useAuthStore } from "@/stores/auth";
import { useAppStore } from "@/stores/app";
import ProductTour, {
  type ProductTourStep,
} from "@/components/ProductTour.vue";
import Toast from "@/components/Toast.vue";

const route = useRoute();
const { locale } = useI18n();
const authStore = useAuthStore();
const appStore = useAppStore();
const isOnboardingTourActive = ref(false);
const canRunOnboardingTour = computed(
  () => !!authStore.token && route.meta.requiresAuth !== false,
);

const onboardingTourSteps = computed<ProductTourStep[]>(() => {
  const zh = locale.value === "zh-CN";
  return [
    {
      route: "/",
      selector: '[data-tour="dashboard-setup-guide"]',
      title: zh ? "从配置向导开始" : "Start with the setup guide",
      description: zh
        ? "这里是完整配置流程的入口。后续步骤会自动跳转到对应页面，并框选左侧菜单入口，帮你建立模块路径。"
        : "This is the entry point for the full setup workflow. The tour will move across pages and highlight sidebar entries so you understand the module path.",
    },
    {
      route: "/proxies",
      selector: '[data-tour="nav-proxies"]',
      title: zh ? "从菜单进入 Proxy" : "Open Proxies from the menu",
      description: zh
        ? "左侧 Resources 下的 Proxies 是执行节点入口。这里可以管理负责备份、同步、维护等任务的 Proxy。"
        : "Proxies live under Resources in the sidebar. This is where you manage nodes that run backup, sync, and maintenance work.",
    },
    {
      route: "/gateways",
      selector: '[data-tour="nav-gateways"]',
      title: zh ? "从菜单进入 Gateway" : "Open Gateways from the menu",
      description: zh
        ? "Gateway 也在 Resources 分组下，主要承载快照索引和 AI 洞察链路。"
        : "Gateways are also under Resources and power snapshot indexing plus the AI insight workflow.",
    },
    {
      route: "/source-resources",
      selector: '[data-tour="nav-source-resources"]',
      title: zh ? "从菜单进入数据源" : "Open Source Resources from the menu",
      description: zh
        ? "Source Resources 是源端资源入口，先把要保护的数据源登记到这里。"
        : "Source Resources is the entry for protected source data. Register the data you want to protect here first.",
    },
    {
      route: "/repository",
      selector: '[data-tour="nav-repository"]',
      title: zh ? "从菜单进入仓库" : "Open Repository from the menu",
      description: zh
        ? "Repository 是目标仓库入口，用来管理保存 Kopia 快照的位置。"
        : "Repository is where you manage the target storage locations that hold Kopia snapshots.",
    },
    {
      route: "/policies",
      selector: '[data-tour="nav-policies"]',
      title: zh ? "从菜单进入策略" : "Open Policies from the menu",
      description: zh
        ? "Policies 在 Data Protection 分组下，负责定义自动备份使用的统一规则。"
        : "Policies live under Data Protection and define the shared rules used by automated backups.",
    },
    {
      route: "/backup-tasks",
      selector: '[data-tour="nav-backup-tasks"]',
      title: zh ? "从菜单进入备份任务" : "Open Backup Tasks from the menu",
      description: zh
        ? "Backup Tasks 是创建和查看备份任务的主入口，位于 Data Protection 分组下。"
        : "Backup Tasks is the main entry for creating and tracking backup jobs under Data Protection.",
    },
    {
      route: "/ai-insights/overview",
      selector: '[data-tour="nav-ai-insights-overview"]',
      title: zh ? "从菜单进入 AI 洞察" : "Open AI Insights from the menu",
      description: zh
        ? "AI Insights 有独立分组，索引完成后可以从 Overview 进入整体数据洞察。"
        : "AI Insights has its own sidebar group. Start from Overview after snapshots have been indexed.",
    },
    {
      route: "/recovery-tasks",
      selector: '[data-tour="nav-recovery-tasks"]',
      title: zh ? "从菜单进入恢复任务" : "Open Recovery Tasks from the menu",
      description: zh
        ? "Recovery Tasks 也在 Data Protection 分组下，用来验证和执行恢复流程。"
        : "Recovery Tasks also live under Data Protection and are used to verify and run restores.",
    },
  ];
});

function startOnboardingTour() {
  isOnboardingTourActive.value = true;
}

function finishOnboardingTour() {
  isOnboardingTourActive.value = false;
  localStorage.setItem("onboardingTourCompleted", "true");
}

function skipOnboardingTour() {
  isOnboardingTourActive.value = false;
  localStorage.setItem("onboardingTourSkipped", "true");
}

onMounted(async () => {
  window.addEventListener("hfl:start-onboarding-tour", startOnboardingTour);

  // Initialize application
  await appStore.initialize();

  // Check authentication status
  if (authStore.token) {
    await authStore.fetchUser();
  }
});

onBeforeUnmount(() => {
  window.removeEventListener("hfl:start-onboarding-tour", startOnboardingTour);
});

// Watch route changes
watch(
  () => route.path,
  () => {
    // Update page title
    const title = route.meta.title as string;
    document.title = title ? `${title} | HyperFileLens` : "HyperFileLens";
  },
);
</script>

<template>
  <div class="min-h-screen app-background">
    <!-- Main Content -->
    <RouterView />

    <!-- Global Loading Overlay -->
    <Transition name="fade">
      <div
        v-if="appStore.isLoading"
        class="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm"
      >
        <div class="text-center">
          <div class="spinner-lg mx-auto mb-4"></div>
          <p class="text-foreground-secondary">{{ appStore.loadingMessage }}</p>
        </div>
      </div>
    </Transition>

    <!-- Toast Notifications -->
    <Teleport to="body">
      <div
        class="fixed top-4 right-4 z-[100] flex flex-col gap-3 pointer-events-none"
      >
        <TransitionGroup name="toast">
          <Toast
            v-for="toast in appStore.toasts"
            :key="toast.id"
            v-bind="toast"
            @close="appStore.removeToast"
          />
        </TransitionGroup>
      </div>
    </Teleport>

    <ProductTour
      :steps="onboardingTourSteps"
      :active="isOnboardingTourActive && canRunOnboardingTour"
      @finish="finishOnboardingTour"
      @skip="skipOnboardingTour"
    />
  </div>
</template>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.toast-enter-active {
  animation: toast-in 0.3s ease-out;
}

.toast-leave-active {
  animation: toast-out 0.2s ease-in forwards;
}

@keyframes toast-in {
  from {
    opacity: 0;
    transform: translateX(100%) scale(0.9);
  }
  to {
    opacity: 1;
    transform: translateX(0) scale(1);
  }
}

@keyframes toast-out {
  from {
    opacity: 1;
    transform: translateX(0) scale(1);
  }
  to {
    opacity: 0;
    transform: translateX(100%) scale(0.9);
  }
}
</style>
