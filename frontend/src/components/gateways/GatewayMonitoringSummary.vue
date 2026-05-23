<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  CircleStackIcon,
  ClockIcon,
  CpuChipIcon,
  ServerStackIcon,
} from "@heroicons/vue/24/outline";

defineProps<{
  gateway: { last_heartbeat?: string };
  current: Record<string, any>;
  stats: {
    avgCpu: number;
    avgMemory: number;
    avgDisk: number;
    maxCpu: number;
    maxMemory: number;
    maxDisk: number;
  } | null;
}>();

const { t } = useI18n();

function formatUptime(seconds?: number | null): string {
  if (!seconds) return "-";
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}
</script>

<template>
  <div class="grid grid-cols-4 gap-3">
    <div
      class="bg-gradient-to-br from-indigo-50 to-indigo-100 dark:from-indigo-900/30 dark:to-indigo-800/30 rounded-xl p-3"
    >
      <div class="flex items-center gap-2 text-indigo-700 dark:text-indigo-300">
        <CpuChipIcon class="w-4 h-4" />
        <p class="text-xs">{{ t("gateways.monitoring.cpuUsage") }}</p>
      </div>
      <p class="text-xl font-bold text-indigo-700 dark:text-indigo-300 mt-1">
        {{ (current.cpu_usage || 0).toFixed(1) }}%
      </p>
      <p class="text-xs text-foreground-secondary mt-1">
        {{ t("gateways.cpuCores") }}: {{ current.cpu_cores || "-" }}
      </p>
    </div>
    <div
      class="bg-gradient-to-br from-emerald-50 to-emerald-100 dark:from-emerald-900/30 dark:to-emerald-800/30 rounded-xl p-3"
    >
      <div class="flex items-center gap-2 text-emerald-700 dark:text-emerald-300">
        <CircleStackIcon class="w-4 h-4" />
        <p class="text-xs">{{ t("gateways.monitoring.memoryUsage") }}</p>
      </div>
      <p class="text-xl font-bold text-emerald-700 dark:text-emerald-300 mt-1">
        {{ (current.memory_usage || 0).toFixed(1) }}%
      </p>
      <p class="text-xs text-foreground-secondary mt-1">
        {{ t("gateways.memoryTotal") }}:
        {{
          current.memory_total
            ? `${(current.memory_total / 1024 ** 3).toFixed(1)} GB`
            : "-"
        }}
      </p>
    </div>
    <div
      class="bg-gradient-to-br from-amber-50 to-amber-100 dark:from-amber-900/30 dark:to-amber-800/30 rounded-xl p-3"
    >
      <div class="flex items-center gap-2 text-amber-700 dark:text-amber-300">
        <ServerStackIcon class="w-4 h-4" />
        <p class="text-xs">{{ t("gateways.monitoring.diskUsage") }}</p>
      </div>
      <p class="text-xl font-bold text-amber-700 dark:text-amber-300 mt-1">
        {{ (current.disk_usage || 0).toFixed(1) }}%
      </p>
      <p class="text-xs text-foreground-secondary mt-1">
        {{ t("gateways.monitoring.diskTotal") }}:
        {{
          current.disk_total
            ? `${(current.disk_total / 1024 ** 3).toFixed(1)} GB`
            : "-"
        }}
      </p>
    </div>
    <div
      class="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/30 dark:to-blue-800/30 rounded-xl p-3"
    >
      <div class="flex items-center gap-2 text-blue-700 dark:text-blue-300">
        <ClockIcon class="w-4 h-4" />
        <p class="text-xs">{{ t("gateways.monitoring.uptime") }}</p>
      </div>
      <p class="text-xl font-bold text-blue-700 dark:text-blue-300 mt-1">
        {{ formatUptime(current.uptime) }}
      </p>
      <p class="text-xs text-foreground-secondary mt-1">
        {{ t("gateways.lastHeartbeat") }}:
        {{
          gateway.last_heartbeat
            ? new Date(gateway.last_heartbeat).toLocaleTimeString()
            : "-"
        }}
      </p>
    </div>
  </div>
</template>
