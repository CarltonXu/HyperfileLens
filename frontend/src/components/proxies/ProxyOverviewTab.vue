<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  ClipboardDocumentIcon,
  ComputerDesktopIcon,
  CpuChipIcon,
  InformationCircleIcon,
} from "@heroicons/vue/24/outline";

defineProps<{
  data: any;
  getStatusColor: (status: string) => string;
  formatUptime: (seconds: number | null) => string;
}>();

const emit = defineEmits<{
  copy: [text: string, label?: string];
}>();

const { t } = useI18n();
</script>

<template>
  <div class="space-y-6">
    <template v-if="data">
      <div>
        <h3
          class="text-sm font-semibold text-foreground mb-3 flex items-center gap-2"
        >
          <InformationCircleIcon class="w-4 h-4 text-indigo-500" />
          {{ t("proxies.detail.sections.basicInfo") }}
        </h3>
        <div class="bg-background-secondary rounded-xl p-4">
          <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div>
              <p class="text-xs text-foreground-secondary mb-1">
                {{ t("proxies.detail.proxyId") }}
              </p>
              <div class="flex items-center gap-1">
                <p class="text-sm font-mono text-foreground truncate">
                  {{ data.id }}
                </p>
                <button
                  @click="emit('copy', data.id, 'Proxy ID')"
                  class="p-1 text-foreground-muted hover:text-indigo-600"
                >
                  <ClipboardDocumentIcon class="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
            <div>
              <p class="text-xs text-foreground-secondary mb-1">
                {{ t("proxies.detail.role") }}
              </p>
              <p class="text-sm font-medium text-foreground">
                {{ t(`proxies.roles.${data.role}`) }}
              </p>
            </div>
            <div>
              <p class="text-xs text-foreground-secondary mb-1">
                {{ t("proxies.detail.status") }}
              </p>
              <span
                :class="[
                  'px-2 py-0.5 rounded text-xs font-medium',
                  getStatusColor(data.status),
                ]"
              >
                {{ t(`proxies.status.${data.status}`) }}
              </span>
            </div>
            <div>
              <p class="text-xs text-foreground-secondary mb-1">
                {{ t("proxies.detail.createdAt") }}
              </p>
              <p class="text-sm text-foreground">
                {{ new Date(data.created_at).toLocaleString() }}
              </p>
            </div>
            <div>
              <p class="text-xs text-foreground-secondary mb-1">
                {{ t("proxies.detail.owner") }}
              </p>
              <p class="text-sm text-foreground">
                {{ data.owner_name || "-" }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div>
        <h3
          class="text-sm font-semibold text-foreground mb-3 flex items-center gap-2"
        >
          <ComputerDesktopIcon class="w-4 h-4 text-emerald-500" />
          {{ t("proxies.detail.sections.systemInfo") }}
        </h3>
        <div class="bg-background-secondary rounded-xl p-4">
          <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div>
              <p class="text-xs text-foreground-secondary mb-1">
                {{ t("proxies.detail.hostname") }}
              </p>
              <p class="text-sm font-medium text-foreground">
                {{ data.hostname || "-" }}
              </p>
            </div>
            <div>
              <p class="text-xs text-foreground-secondary mb-1">
                {{ t("proxies.detail.internalIp") }}
              </p>
              <p class="text-sm font-medium text-foreground">
                {{ data.internal_ip || "-" }}
              </p>
            </div>
            <div>
              <p class="text-xs text-foreground-secondary mb-1">
                {{ t("proxies.detail.operatingSystem") }}
              </p>
              <p class="text-sm font-medium text-foreground">
                {{ data.operating_system || "-" }}
              </p>
            </div>
            <div>
              <p class="text-xs text-foreground-secondary mb-1">
                {{ t("proxies.detail.proxyVersion") }}
              </p>
              <p class="text-sm font-medium text-foreground">
                {{ data.version || "-" }}
              </p>
            </div>
            <div>
              <p class="text-xs text-foreground-secondary mb-1">
                {{ t("proxies.detail.kopiaVersion") }}
              </p>
              <p class="text-sm font-medium text-foreground">
                {{ data.kopia_version || "-" }}
              </p>
            </div>
            <div>
              <p class="text-xs text-foreground-secondary mb-1">
                {{ t("proxies.detail.uptime") }}
              </p>
              <p class="text-sm font-medium text-foreground">
                {{ formatUptime(data.uptime_seconds) }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div>
        <h3
          class="text-sm font-semibold text-foreground mb-3 flex items-center gap-2"
        >
          <CpuChipIcon class="w-4 h-4 text-amber-500" />
          {{ t("proxies.detail.sections.hardwareResources") }}
        </h3>
        <div class="grid grid-cols-3 gap-4">
          <div class="bg-background-secondary rounded-xl p-4 text-center">
            <p class="text-xs text-foreground-secondary mb-2">
              {{ t("proxies.detail.cpu") }}
            </p>
            <p class="text-3xl font-bold text-foreground">
              {{ (data.cpu_usage || 0).toFixed(1)
              }}<span class="text-lg">%</span>
            </p>
            <div
              class="w-full h-2 bg-slate-200 rounded-full mt-2 overflow-hidden"
            >
              <div
                class="h-full bg-indigo-500 rounded-full transition-all"
                :style="{ width: `${data.cpu_usage || 0}%` }"
              />
            </div>
            <p class="text-xs text-foreground-muted mt-2">
              {{ data.cpu_cores || "-" }} {{ t("proxies.detail.cores") }}
            </p>
          </div>
          <div class="bg-background-secondary rounded-xl p-4 text-center">
            <p class="text-xs text-foreground-secondary mb-2">
              {{ t("proxies.detail.memory") }}
            </p>
            <p class="text-3xl font-bold text-foreground">
              {{ (data.memory_usage || 0).toFixed(1)
              }}<span class="text-lg">%</span>
            </p>
            <div
              class="w-full h-2 bg-slate-200 rounded-full mt-2 overflow-hidden"
            >
              <div
                class="h-full bg-emerald-500 rounded-full transition-all"
                :style="{ width: `${data.memory_usage || 0}%` }"
              />
            </div>
            <p class="text-xs text-foreground-muted mt-2">
              {{
                data.memory_total
                  ? `${(data.memory_total / 1024 ** 3).toFixed(1)} GB`
                  : "-"
              }}
            </p>
          </div>
          <div class="bg-background-secondary rounded-xl p-4 text-center">
            <p class="text-xs text-foreground-secondary mb-2">
              {{ t("proxies.detail.disk") }}
            </p>
            <p class="text-3xl font-bold text-foreground">
              {{ (data.disk_usage || 0).toFixed(1)
              }}<span class="text-lg">%</span>
            </p>
            <div
              class="w-full h-2 bg-slate-200 rounded-full mt-2 overflow-hidden"
            >
              <div
                class="h-full bg-amber-500 rounded-full transition-all"
                :style="{ width: `${data.disk_usage || 0}%` }"
              />
            </div>
            <p class="text-xs text-foreground-muted mt-2">
              {{
                data.disk_total
                  ? `${(data.disk_total / 1024 ** 3).toFixed(1)} GB`
                  : "-"
              }}
            </p>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div class="bg-background-secondary rounded-xl p-4">
          <h4 class="text-sm font-semibold text-foreground mb-3">
            {{ t("proxies.detail.heartbeatStats") }}
          </h4>
          <div class="space-y-2">
            <div class="flex justify-between">
              <span class="text-xs text-foreground-secondary">
                {{ t("proxies.detail.heartbeats24h") }}
              </span>
              <span class="text-sm font-medium text-foreground">
                {{ data.stats?.heartbeats_24h || 0 }}
              </span>
            </div>
            <div class="flex justify-between">
              <span class="text-xs text-foreground-secondary">
                {{ t("proxies.detail.expected24h") }}
              </span>
              <span class="text-sm font-medium text-foreground">
                {{ data.stats?.expected_24h || 0 }}
              </span>
            </div>
            <div class="flex justify-between">
              <span class="text-xs text-foreground-secondary">
                {{ t("proxies.detail.missedHeartbeats") }}
              </span>
              <span
                class="text-sm font-medium"
                :class="
                  data.stats?.missed_heartbeats > 0
                    ? 'text-amber-600 dark:text-amber-400'
                    : 'text-foreground'
                "
              >
                {{ data.stats?.missed_heartbeats || 0 }}
              </span>
            </div>
          </div>
        </div>
        <div class="bg-background-secondary rounded-xl p-4">
          <h4 class="text-sm font-semibold text-foreground mb-3">
            {{ t("proxies.detail.taskStats") }}
          </h4>
          <div class="space-y-2">
            <div class="flex justify-between">
              <span class="text-xs text-foreground-secondary">
                {{ t("proxies.detail.totalTasks") }}
              </span>
              <span class="text-sm font-medium text-foreground">
                {{ data.task_stats?.total || 0 }}
              </span>
            </div>
            <div class="flex justify-between">
              <span class="text-xs text-foreground-secondary">
                {{ t("proxies.detail.completed") }}
              </span>
              <span
                class="text-sm font-medium text-emerald-600 dark:text-emerald-400"
              >
                {{ data.task_stats?.completed || 0 }}
              </span>
            </div>
            <div class="flex justify-between">
              <span class="text-xs text-foreground-secondary">
                {{ t("proxies.detail.failed") }}
              </span>
              <span class="text-sm font-medium text-red-600">
                {{ data.task_stats?.failed || 0 }}
              </span>
            </div>
            <div class="flex justify-between">
              <span class="text-xs text-foreground-secondary">
                {{ t("proxies.detail.running") }}
              </span>
              <span class="text-sm font-medium text-blue-600">
                {{ data.task_stats?.running || 0 }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
