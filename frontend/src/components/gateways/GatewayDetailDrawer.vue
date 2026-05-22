<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  ArrowPathIcon,
  ServerIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline";

type DetailTab = "overview" | "mounts" | "monitoring";

interface Gateway {
  id: string;
  name: string;
  status: string;
  is_online: boolean;
  [key: string]: any;
}

defineProps<{
  gateway: Gateway | null;
  detailTab: DetailTab;
  loading: boolean;
  statusColors: Record<string, string>;
}>();

const emit = defineEmits<{
  close: [];
  refresh: [];
  "update:detailTab": [tab: DetailTab];
}>();

const { t } = useI18n();

const tabs: DetailTab[] = ["overview", "mounts", "monitoring"];

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    pending: t("gateways.statusPending"),
    installing: t("gateways.statusInstalling"),
    active: t("gateways.statusActive"),
    inactive: t("gateways.statusInactive"),
    offline: t("gateways.statusOffline"),
    error: t("gateways.statusError"),
    maintenance: t("gateways.statusMaintenance"),
  };
  return labels[status] || status;
}
</script>

<template>
  <Transition name="drawer">
    <div class="fixed inset-0 z-50">
      <div class="absolute inset-0 bg-black/50" @click="emit('close')"></div>

      <div
        class="absolute top-0 right-0 h-full w-[75%] drawer-panel shadow-2xl flex flex-col"
      >
        <!-- Header -->
        <div
          class="flex items-center justify-between p-5 border-b border-border drawer-surface flex-shrink-0"
        >
          <div class="flex items-center gap-3">
            <div
              :class="[
                'w-10 h-10 rounded-xl flex items-center justify-center',
                gateway?.is_online
                  ? 'bg-gradient-to-br from-emerald-500 to-teal-600'
                  : 'bg-gradient-to-br from-slate-400 to-slate-500',
              ]"
            >
              <ServerIcon class="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 class="text-lg font-semibold text-foreground">
                {{ gateway?.name }}
              </h2>
              <div class="flex items-center gap-2 mt-1">
                <span
                  :class="[
                    'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium',
                    statusColors[gateway?.status || 'pending'],
                  ]"
                >
                  {{ getStatusLabel(gateway?.status || "pending") }}
                </span>
                <span
                  v-if="gateway?.is_online"
                  class="px-2 py-0.5 bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 rounded-full text-xs font-medium"
                >
                  {{ t("gateways.online") }}
                </span>
                <span
                  v-else
                  class="px-2 py-0.5 bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 rounded-full text-xs font-medium"
                >
                  {{ t("gateways.offline") }}
                </span>
              </div>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <button
              @click="emit('refresh')"
              class="p-2 text-foreground-muted hover:text-foreground-secondary hover:bg-hover rounded-lg"
              :title="t('common.refresh')"
            >
              <ArrowPathIcon class="w-5 h-5" />
            </button>
            <button
              @click="emit('close')"
              class="p-2 text-foreground-muted hover:text-foreground-secondary hover:bg-hover rounded-lg"
            >
              <XMarkIcon class="w-5 h-5" />
            </button>
          </div>
        </div>

        <!-- Tabs -->
        <div
          class="border-b border-border drawer-muted-surface px-5 flex-shrink-0"
        >
          <nav class="flex gap-1 -mb-px">
            <button
              v-for="tab in tabs"
              :key="tab"
              @click="emit('update:detailTab', tab)"
              :class="[
                'px-4 py-3 text-sm font-medium border-b-2 transition-colors',
                detailTab === tab
                  ? 'border-violet-500 text-violet-600'
                  : 'border-transparent text-foreground-secondary hover:text-foreground hover:border-slate-300 dark:hover:border-slate-600',
              ]"
            >
              {{ t(`gateways.tabs.${tab}`) }}
            </button>
          </nav>
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-y-auto p-5 bg-background text-foreground">
          <div v-if="loading" class="flex items-center justify-center py-12">
            <ArrowPathIcon class="w-6 h-6 text-violet-500 animate-spin" />
          </div>
          <slot v-else />
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.drawer-panel,
.drawer-surface {
  background-color: var(--card);
  color: var(--foreground);
}

.drawer-muted-surface {
  background-color: var(--background-secondary);
}

.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 0.3s ease;
}

.drawer-enter-active .absolute.top-0.right-0,
.drawer-leave-active .absolute.top-0.right-0 {
  transition: transform 0.3s ease;
}

.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}

.drawer-enter-from .absolute.top-0.right-0,
.drawer-leave-to .absolute.top-0.right-0 {
  transform: translateX(100%);
}

.drawer-enter-active .absolute.inset-0.bg-black\/50,
.drawer-leave-active .absolute.inset-0.bg-black\/50 {
  transition: opacity 0.3s ease;
}
</style>
