<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  CpuChipIcon,
  EllipsisHorizontalIcon,
  ExclamationTriangleIcon,
  MapPinIcon,
  PlusIcon,
  ServerIcon,
} from "@heroicons/vue/24/outline";
import type { ProxyNode } from "@/types/proxy";
import ProxyActionMenu from "./ProxyActionMenu.vue";

defineProps<{
  loading: boolean;
  filteredCount: number;
  proxies: ProxyNode[];
  openMenuId: string | null;
  menuStyle: Record<string, string>;
  agentIcon: any;
  syncIcon: any;
  getRoleColor: (role: string) => string;
  getStatusColor: (status: string) => string;
  getStatusIcon: (status: string) => any;
  timeSince: (date: string | null) => string;
}>();

defineEmits<{
  install: [];
  toggleMenu: [proxyId: string, event: Event];
  closeMenu: [];
  detail: [proxy: ProxyNode];
  edit: [proxy: ProxyNode];
  regenerateToken: [proxy: ProxyNode];
  updateStatus: [proxy: ProxyNode, status: string];
  delete: [proxy: ProxyNode];
  installInfo: [proxy: ProxyNode];
}>();

const { t } = useI18n();
</script>

<template>
  <template v-if="loading">
    <div class="flex items-center justify-center py-12">
      <div
        class="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"
      />
    </div>
  </template>

  <div
    v-else-if="filteredCount === 0"
    class="bg-card rounded-xl border border-border p-12 text-center"
  >
    <div
      class="w-16 h-16 bg-background-tertiary rounded-full flex items-center justify-center mx-auto mb-4"
    >
      <ServerIcon class="w-8 h-8 text-foreground-muted" />
    </div>
    <h3 class="text-lg font-medium text-foreground mb-1">
      {{ t("proxies.empty.title") }}
    </h3>
    <p class="text-foreground-secondary">
      {{ t("proxies.empty.description") }}
    </p>
    <button
      class="mt-4 inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
      @click="$emit('install')"
    >
      <PlusIcon class="w-4 h-4" />
      {{ t("proxies.installProxy") }}
    </button>
  </div>

  <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
    <div
      v-for="proxy in proxies"
      :key="proxy.id"
      class="bg-card rounded-xl border border-border p-5 shadow-sm hover:shadow-md hover:border-slate-300 dark:hover:border-slate-600 transition-all group"
    >
      <div class="flex items-start justify-between mb-4">
        <div class="flex items-center gap-3">
          <div
            :class="[
              'w-11 h-11 rounded-xl flex items-center justify-center',
              proxy.role === 'agent'
                ? 'bg-gradient-to-br from-indigo-500 to-blue-600'
                : 'bg-gradient-to-br from-purple-500 to-violet-600',
            ]"
          >
            <component
              :is="proxy.role === 'agent' ? agentIcon : syncIcon"
              class="w-6 h-6 text-white"
            />
          </div>
          <div>
            <h3
              class="font-semibold text-foreground group-hover:text-indigo-600 transition-colors"
            >
              {{ proxy.name }}
            </h3>
            <span
              :class="[
                'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium mt-1',
                getRoleColor(proxy.role),
              ]"
            >
              {{ t(`proxies.roles.${proxy.role}`) }}
            </span>
          </div>
        </div>
        <div class="relative" @click.stop>
          <button
            class="p-1.5 text-foreground-muted hover:text-foreground-secondary hover:bg-hover rounded-lg transition-colors"
            @click="$emit('toggleMenu', proxy.id, $event)"
          >
            <EllipsisHorizontalIcon class="w-5 h-5" />
          </button>
          <ProxyActionMenu
            :proxy="proxy"
            :open="openMenuId === proxy.id"
            :menu-style="menuStyle"
            @close="$emit('closeMenu')"
            @detail="$emit('detail', $event)"
            @edit="$emit('edit', $event)"
            @regenerate-token="$emit('regenerateToken', $event)"
            @update-status="
              (item, status) => $emit('updateStatus', item, status)
            "
            @delete="$emit('delete', $event)"
          />
        </div>
      </div>

      <div class="space-y-3 text-sm">
        <div class="flex items-center gap-2 text-foreground-secondary">
          <MapPinIcon class="w-4 h-4 flex-shrink-0" />
          <span class="truncate">{{
            proxy.hostname || proxy.internal_ip || t("proxies.noConnection")
          }}</span>
        </div>
        <div class="flex items-center gap-2 text-foreground-secondary">
          <component
            :is="getStatusIcon('pending')"
            class="w-4 h-4 flex-shrink-0"
          />
          <span>{{ timeSince(proxy.last_heartbeat) }}</span>
        </div>
        <div class="flex items-center gap-2 text-foreground-secondary">
          <CpuChipIcon class="w-4 h-4 flex-shrink-0" />
          <span>
            {{ proxy.operating_system || "Unknown" }}
            {{ proxy.cpu_cores ? `(${proxy.cpu_cores} cores)` : "" }}
          </span>
        </div>
      </div>

      <div
        v-if="proxy.cpu_usage !== null"
        class="mt-4 grid grid-cols-3 gap-2 text-center"
      >
        <div class="bg-background-secondary rounded-lg p-2">
          <p class="text-xs text-foreground-secondary">CPU</p>
          <p class="text-sm font-medium text-foreground">
            {{ proxy.cpu_usage?.toFixed(1) }}%
          </p>
        </div>
        <div class="bg-background-secondary rounded-lg p-2">
          <p class="text-xs text-foreground-secondary">Memory</p>
          <p class="text-sm font-medium text-foreground">
            {{ proxy.memory_usage?.toFixed(1) }}%
          </p>
        </div>
        <div class="bg-background-secondary rounded-lg p-2">
          <p class="text-xs text-foreground-secondary">Disk</p>
          <p class="text-sm font-medium text-foreground">
            {{ proxy.disk_usage?.toFixed(1) }}%
          </p>
        </div>
      </div>

      <div
        class="flex items-center justify-between mt-4 pt-4 border-t border-border"
      >
        <div class="flex items-center gap-1.5">
          <component
            :is="getStatusIcon(proxy.status)"
            :class="[
              'w-4 h-4',
              proxy.status === 'online'
                ? 'text-emerald-500'
                : proxy.status === 'error'
                  ? 'text-red-500'
                  : 'text-foreground-muted',
            ]"
          />
          <span
            :class="[
              'text-xs font-medium',
              getStatusColor(proxy.status).split(' ').slice(1).join(' '),
            ]"
          >
            {{ t(`proxies.status.${proxy.status}`) }}
          </span>
        </div>
        <div class="flex items-center gap-2">
          <button
            v-if="proxy.status === 'pending'"
            class="text-sm font-medium text-amber-600 dark:text-amber-400 hover:text-amber-700 flex items-center gap-1"
            @click="$emit('installInfo', proxy)"
          >
            <ExclamationTriangleIcon class="w-4 h-4" />
            {{ t("proxies.actions.viewInstall") }}
          </button>
          <button
            class="text-sm font-medium text-indigo-600 hover:text-indigo-700"
            @click="$emit('detail', proxy)"
          >
            {{ t("proxies.actions.viewDetails") }} →
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
