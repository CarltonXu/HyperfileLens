<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  ArrowPathIcon,
  CpuChipIcon,
  CircleStackIcon,
  ArrowTrendingUpIcon,
} from "@heroicons/vue/24/outline";

interface HeartbeatData {
  timestamp: string;
  cpu_usage: number | null;
  memory_usage: number | null;
  disk_usage: number | null;
  active_mounts: number;
  network_bytes_sent?: number;
  network_bytes_recv?: number;
}

interface Gateway {
  id: string;
  name: string;
}

defineProps<{
  gateway: Gateway;
  monitoringData: HeartbeatData[];
  isLoading: boolean;
  timeRange: number;
  stats: {
    avgCpu: number;
    avgMemory: number;
    avgDisk: number;
    maxCpu: number;
    maxMemory: number;
    maxDisk: number;
  } | null;
}>();

defineEmits<{
  refresh: [];
  "update:timeRange": [value: number];
}>();

const { t } = useI18n();

const timeRanges = [
  { value: 1, label: "1h" },
  { value: 6, label: "6h" },
  { value: 24, label: "24h" },
  { value: 168, label: "7d" },
];

function formatDate(dateStr: string): string {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleString();
}
</script>

<template>
  <div class="space-y-6">
    <!-- Time Range Selector -->
    <div class="flex items-center justify-between">
      <h3 class="text-sm font-semibold text-foreground">
        {{ t("gateways.monitoring.title") }}
      </h3>
      <div class="flex items-center gap-2">
        <select
          :value="timeRange"
          @change="$emit('update:timeRange', Number(($event.target as HTMLSelectElement).value))"
          class="px-3 py-1.5 border border-border rounded-lg bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
        >
          <option
            v-for="range in timeRanges"
            :key="range.value"
            :value="range.value"
          >
            {{ range.label }}
          </option>
        </select>
        <button
          @click="$emit('refresh')"
          class="p-1.5 text-foreground-muted hover:text-foreground-secondary hover:bg-hover rounded-lg"
          :title="t('common.refresh')"
        >
          <ArrowPathIcon class="w-4 h-4" />
        </button>
      </div>
    </div>

    <!-- Stats Summary -->
    <div v-if="stats" class="grid grid-cols-3 gap-4">
      <div class="bg-background-secondary rounded-lg p-4">
        <div class="flex items-center gap-2 text-foreground-secondary mb-2">
          <CpuChipIcon class="w-4 h-4" />
          <span class="text-sm">{{ t("gateways.monitoring.cpu") }}</span>
        </div>
        <p class="text-2xl font-bold text-foreground">
          {{ stats.avgCpu.toFixed(1) }}%
        </p>
        <p class="text-xs text-foreground-secondary mt-1">
          {{ t("gateways.monitoring.max") }}: {{ stats.maxCpu.toFixed(1) }}%
        </p>
      </div>
      <div class="bg-background-secondary rounded-lg p-4">
        <div class="flex items-center gap-2 text-foreground-secondary mb-2">
          <CircleStackIcon class="w-4 h-4" />
          <span class="text-sm">{{ t("gateways.monitoring.memory") }}</span>
        </div>
        <p class="text-2xl font-bold text-foreground">
          {{ stats.avgMemory.toFixed(1) }}%
        </p>
        <p class="text-xs text-foreground-secondary mt-1">
          {{ t("gateways.monitoring.max") }}: {{ stats.maxMemory.toFixed(1) }}%
        </p>
      </div>
      <div class="bg-background-secondary rounded-lg p-4">
        <div class="flex items-center gap-2 text-foreground-secondary mb-2">
          <ArrowTrendingUpIcon class="w-4 h-4" />
          <span class="text-sm">{{ t("gateways.monitoring.disk") }}</span>
        </div>
        <p class="text-2xl font-bold text-foreground">
          {{ stats.avgDisk.toFixed(1) }}%
        </p>
        <p class="text-xs text-foreground-secondary mt-1">
          {{ t("gateways.monitoring.max") }}: {{ stats.maxDisk.toFixed(1) }}%
        </p>
      </div>
    </div>

    <!-- Loading State -->
    <div
      v-if="isLoading"
      class="flex items-center justify-center py-12"
    >
      <ArrowPathIcon class="w-6 h-6 text-violet-500 animate-spin" />
    </div>

    <!-- Empty State -->
    <div
      v-else-if="monitoringData.length === 0"
      class="text-center py-12"
    >
      <p class="text-foreground-secondary">
        {{ t("gateways.monitoring.empty") }}
      </p>
    </div>

    <!-- Data Chart -->
    <div v-else class="bg-background-secondary rounded-lg p-4">
      <h4 class="text-sm font-medium text-foreground mb-4">
        {{ t("gateways.monitoring.resourceUsage") }}
      </h4>
      <div class="h-64 flex items-end gap-1">
        <div
          v-for="(data, index) in monitoringData.slice(-48)"
          :key="index"
          class="flex-1 flex flex-col gap-0.5"
        >
          <!-- CPU Bar -->
          <div
            class="bg-indigo-500 rounded-t"
            :style="{ height: `${data.cpu_usage || 0}%` }"
            :title="`CPU: ${data.cpu_usage?.toFixed(1) || 0}%`"
          />
          <!-- Memory Bar -->
          <div
            class="bg-emerald-500"
            :style="{ height: `${data.memory_usage || 0}%` }"
            :title="`Memory: ${data.memory_usage?.toFixed(1) || 0}%`"
          />
          <!-- Disk Bar -->
          <div
            class="bg-amber-500"
            :style="{ height: `${data.disk_usage || 0}%` }"
            :title="`Disk: ${data.disk_usage?.toFixed(1) || 0}%`"
          />
        </div>
      </div>
      <div class="flex items-center justify-center gap-6 mt-4 text-xs text-foreground-secondary">
        <div class="flex items-center gap-1">
          <div class="w-3 h-3 bg-indigo-500 rounded" />
          <span>{{ t("gateways.monitoring.cpu") }}</span>
        </div>
        <div class="flex items-center gap-1">
          <div class="w-3 h-3 bg-emerald-500 rounded" />
          <span>{{ t("gateways.monitoring.memory") }}</span>
        </div>
        <div class="flex items-center gap-1">
          <div class="w-3 h-3 bg-amber-500 rounded" />
          <span>{{ t("gateways.monitoring.disk") }}</span>
        </div>
      </div>
    </div>

    <!-- Recent Heartbeats Table -->
    <div v-if="monitoringData.length > 0">
      <h4 class="text-sm font-medium text-foreground mb-3">
        {{ t("gateways.monitoring.recentHeartbeats") }}
      </h4>
      <div class="bg-background-secondary rounded-lg overflow-hidden">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-border">
              <th class="text-left px-4 py-3 text-foreground-secondary font-medium">
                {{ t("gateways.monitoring.time") }}
              </th>
              <th class="text-right px-4 py-3 text-foreground-secondary font-medium">
                {{ t("gateways.monitoring.cpu") }}
              </th>
              <th class="text-right px-4 py-3 text-foreground-secondary font-medium">
                {{ t("gateways.monitoring.memory") }}
              </th>
              <th class="text-right px-4 py-3 text-foreground-secondary font-medium">
                {{ t("gateways.monitoring.disk") }}
              </th>
              <th class="text-right px-4 py-3 text-foreground-secondary font-medium">
                {{ t("gateways.mounts.active") }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(data, index) in monitoringData.slice(-10).reverse()"
              :key="index"
              class="border-b border-border last:border-0"
            >
              <td class="px-4 py-2.5 text-foreground-secondary">
                {{ formatDate(data.timestamp) }}
              </td>
              <td class="px-4 py-2.5 text-right text-foreground">
                {{ data.cpu_usage?.toFixed(1) || "-" }}%
              </td>
              <td class="px-4 py-2.5 text-right text-foreground">
                {{ data.memory_usage?.toFixed(1) || "-" }}%
              </td>
              <td class="px-4 py-2.5 text-right text-foreground">
                {{ data.disk_usage?.toFixed(1) || "-" }}%
              </td>
              <td class="px-4 py-2.5 text-right text-foreground">
                {{ data.active_mounts || 0 }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
