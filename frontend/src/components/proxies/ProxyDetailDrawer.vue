<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  ArrowPathIcon,
  CircleStackIcon,
  ComputerDesktopIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline";
import type { ProxyNode } from "@/types/proxy";

type DetailTab = "overview" | "install" | "monitor" | "tasks" | "heartbeats";

defineProps<{
  proxy: ProxyNode | null;
  detailTab: DetailTab;
  loading: boolean;
  getRoleColor: (role: string) => string;
  getStatusColor: (status: string) => string;
}>();

const emit = defineEmits<{
  close: [];
  refresh: [];
  "update:detailTab": [tab: DetailTab];
}>();

const { t } = useI18n();

const tabs: DetailTab[] = ["overview", "monitor", "tasks", "heartbeats"];
</script>

<template>
  <Transition name="drawer">
    <div class="fixed inset-0 z-50">
      <div class="absolute inset-0 bg-black/50" @click="emit('close')"></div>

      <div
        class="absolute top-0 right-0 h-full w-[75%] drawer-panel shadow-2xl flex flex-col"
      >
        <div
          class="flex items-center justify-between p-5 border-b border-border drawer-surface flex-shrink-0"
        >
          <div class="flex items-center gap-3">
            <div
              :class="[
                'w-10 h-10 rounded-xl flex items-center justify-center',
                proxy?.role === 'agent'
                  ? 'bg-gradient-to-br from-indigo-500 to-blue-600'
                  : 'bg-gradient-to-br from-purple-500 to-violet-600',
              ]"
            >
              <component
                :is="
                  proxy?.role === 'agent'
                    ? ComputerDesktopIcon
                    : CircleStackIcon
                "
                class="w-5 h-5 text-white"
              />
            </div>
            <div>
              <h2 class="text-lg font-semibold text-foreground">
                {{ proxy?.name }}
              </h2>
              <div class="flex items-center gap-2 mt-1">
                <span
                  :class="[
                    'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium',
                    getRoleColor(proxy?.role || 'agent'),
                  ]"
                >
                  {{ t(`proxies.roles.${proxy?.role}`) }}
                </span>
                <span
                  :class="[
                    'px-2 py-0.5 rounded-full text-xs font-medium',
                    getStatusColor(proxy?.status || 'pending'),
                  ]"
                >
                  {{ t(`proxies.status.${proxy?.status}`) }}
                </span>
                <span
                  v-if="proxy?.is_online"
                  class="px-2 py-0.5 bg-emerald-100 text-emerald-700 rounded-full text-xs font-medium"
                >
                  {{ t("proxies.online") }}
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
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-foreground-secondary hover:text-foreground hover:border-slate-300 dark:hover:border-slate-600',
              ]"
            >
              {{ t(`proxies.detail.tabs.${tab}`) }}
            </button>
            <button
              v-if="proxy?.status === 'pending'"
              @click="emit('update:detailTab', 'install')"
              :class="[
                'px-4 py-3 text-sm font-medium border-b-2 transition-colors',
                detailTab === 'install'
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-foreground-secondary hover:text-foreground hover:border-slate-300 dark:hover:border-slate-600',
              ]"
            >
              {{ t("proxies.detail.tabs.install") }}
            </button>
          </nav>
        </div>

        <div class="flex-1 overflow-y-auto p-5 bg-background text-foreground">
          <div v-if="loading" class="flex items-center justify-center py-12">
            <ArrowPathIcon class="w-6 h-6 text-indigo-500 animate-spin" />
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
