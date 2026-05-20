<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { LineChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
} from "echarts/components";
import VChart from "vue-echarts";
import {
  ArrowPathIcon,
  CalendarIcon,
  CircleStackIcon,
  ClockIcon,
  CpuChipIcon,
  WifiIcon,
} from "@heroicons/vue/24/outline";

use([
  CanvasRenderer,
  LineChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
]);

type MonitorRange = "1h" | "6h" | "24h" | "7d" | "30d" | "custom";

const props = defineProps<{
  data: any;
  interval: number;
  monitorTimeRange: MonitorRange;
  customTimeRange: { start: string; end: string };
  showCustomDatePicker: boolean;
  selectedDiskIO: string;
  selectedNetIOInterface: string;
  networkIOStats: {
    rxPackets: number;
    txPackets: number;
    rxDrop: number;
    txErrs: number;
  };
  uniqueDisks: string[];
  uniqueNetworkInterfaces: string[];
  getCPUChartOption: () => any;
  getMemoryChartOption: () => any;
  getDiskChartOption: () => any;
  getDiskUtilAwaitChartOption: () => any;
  getDiskIOPSChartOption: () => any;
  getDiskBandwidthChartOption: () => any;
  getNetworkBytesChartOption: () => any;
  getNetworkPacketsChartOption: () => any;
  formatUptime: (seconds: number | null) => string;
  formatBytes: (bytes?: number | null) => string;
  formatNumber: (num?: number | null) => string;
}>();

const emit = defineEmits<{
  "update:interval": [value: number];
  "update:selectedDiskIO": [value: string];
  "update:selectedNetIOInterface": [value: string];
  "set-auto-refresh": [interval: number];
  refresh: [];
  "set-time-range": [range: MonitorRange];
  "apply-custom-time-range": [];
}>();

const { t } = useI18n();

const refreshInterval = computed({
  get: () => props.interval,
  set: (value: number) => emit("update:interval", Number(value)),
});

const diskIO = computed({
  get: () => props.selectedDiskIO,
  set: (value: string) => emit("update:selectedDiskIO", value),
});

const netIOInterface = computed({
  get: () => props.selectedNetIOInterface,
  set: (value: string) => emit("update:selectedNetIOInterface", value),
});
</script>

<template>
  <div class="space-y-4">
    <div
      class="flex items-center justify-between bg-background-secondary rounded-xl p-3"
    >
      <div class="flex items-center gap-2">
        <ClockIcon class="w-4 h-4 text-foreground-secondary" />
        <span class="text-sm text-foreground-secondary">
          {{ t("proxies.monitoring.autoRefresh") }}
        </span>
      </div>
      <div class="flex items-center gap-2">
        <select
          v-model="refreshInterval"
          @change="emit('set-auto-refresh', refreshInterval)"
          class="text-sm bg-background text-foreground border border-border rounded-lg px-2 py-1 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option :value="0">{{ t("proxies.monitoring.refreshOff") }}</option>
          <option :value="10">{{ t("proxies.monitoring.refresh10s") }}</option>
          <option :value="30">{{ t("proxies.monitoring.refresh30s") }}</option>
          <option :value="60">{{ t("proxies.monitoring.refresh1m") }}</option>
          <option :value="300">{{ t("proxies.monitoring.refresh5m") }}</option>
        </select>
        <button
          @click="emit('refresh')"
          class="p-1.5 text-foreground-secondary hover:text-indigo-600 hover:bg-card rounded-lg"
          :title="t('proxies.monitoring.refreshNow')"
        >
          <ArrowPathIcon class="w-4 h-4" />
        </button>
      </div>
    </div>

    <template v-if="data">
      <div
        class="flex items-center justify-between bg-background-secondary rounded-xl p-4"
      >
        <div class="flex items-center gap-2">
          <CalendarIcon class="w-5 h-5 text-foreground-secondary" />
          <span class="text-sm font-medium text-foreground">
            {{ t("proxies.monitoring.timeRange") }}
          </span>
        </div>
        <div class="flex items-center gap-2">
          <button
            v-for="range in ['1h', '6h', '24h', '7d', '30d']"
            :key="range"
            @click="emit('set-time-range', range as MonitorRange)"
            :class="[
              'px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
              monitorTimeRange === range
                ? 'bg-indigo-500 text-white'
                : 'bg-card text-foreground-secondary hover:bg-hover border border-border',
            ]"
          >
            {{ range }}
          </button>
          <button
            @click="emit('set-time-range', 'custom')"
            :class="[
              'px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
              monitorTimeRange === 'custom'
                ? 'bg-indigo-500 text-white'
                : 'bg-card text-foreground-secondary hover:bg-hover border border-border',
            ]"
          >
            {{ t("proxies.monitoring.custom") }}
          </button>
        </div>
      </div>

      <div
        v-if="showCustomDatePicker"
        class="bg-background-secondary rounded-xl p-4"
      >
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs text-foreground-secondary mb-1">
              {{ t("proxies.detail.startTime") }}
            </label>
            <input
              v-model="customTimeRange.start"
              type="datetime-local"
              class="w-full px-3 py-2 text-sm border border-border rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>
          <div>
            <label class="block text-xs text-foreground-secondary mb-1">
              {{ t("proxies.detail.endTime") }}
            </label>
            <input
              v-model="customTimeRange.end"
              type="datetime-local"
              class="w-full px-3 py-2 text-sm border border-border rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>
        </div>
        <button
          @click="emit('apply-custom-time-range')"
          class="mt-3 px-4 py-2 text-sm font-medium bg-indigo-500 text-white rounded-lg hover:bg-indigo-600"
        >
          {{ t("proxies.detail.apply") }}
        </button>
      </div>

      <div class="grid grid-cols-4 gap-3">
        <div
          class="bg-gradient-to-br from-indigo-50 to-indigo-100 dark:from-indigo-900/30 dark:to-indigo-800/30 rounded-xl p-3"
        >
          <p class="text-xs text-foreground-secondary opacity-80">
            {{ t("proxies.monitoring.cpuUsage") }}
          </p>
          <p
            class="text-xl font-bold text-indigo-700 dark:text-indigo-400 mt-1"
          >
            {{ (data.current?.cpu_usage || 0).toFixed(1) }}%
          </p>
          <p class="text-xs text-foreground-secondary opacity-70 mt-1">
            {{ t("proxies.monitoring.cpuCores") }}:
            {{ data.current?.cpu_cores || "-" }}
          </p>
        </div>
        <div
          class="bg-gradient-to-br from-emerald-50 to-emerald-100 dark:from-emerald-900/30 dark:to-emerald-800/30 rounded-xl p-3"
        >
          <p class="text-xs text-foreground-secondary opacity-80">
            {{ t("proxies.monitoring.memoryUsage") }}
          </p>
          <p
            class="text-xl font-bold text-emerald-700 dark:text-emerald-400 mt-1"
          >
            {{ (data.current?.memory_usage || 0).toFixed(1) }}%
          </p>
          <p class="text-xs text-foreground-secondary opacity-70 mt-1">
            {{ t("proxies.monitoring.memoryTotal") }}:
            {{ data.current?.memory_total_gb || "-" }} GB
          </p>
        </div>
        <div
          class="bg-gradient-to-br from-amber-50 to-amber-100 dark:from-amber-900/30 dark:to-amber-800/30 rounded-xl p-3"
        >
          <p class="text-xs text-foreground-secondary opacity-80">
            {{ t("proxies.monitoring.diskUsage") }}
          </p>
          <p class="text-xl font-bold text-amber-700 dark:text-amber-400 mt-1">
            {{ (data.current?.disk_usage || 0).toFixed(1) }}%
          </p>
          <p class="text-xs text-foreground-secondary opacity-70 mt-1">
            {{ t("proxies.monitoring.diskTotal") }}:
            {{ data.current?.disk_total_gb || "-" }} GB
          </p>
        </div>
        <div
          class="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/30 dark:to-blue-800/30 rounded-xl p-3"
        >
          <p class="text-xs text-foreground-secondary opacity-80">
            {{ t("proxies.detail.uptime") }}
          </p>
          <p class="text-xl font-bold text-blue-700 dark:text-blue-400 mt-1">
            {{ formatUptime(data.uptime_seconds) }}
          </p>
          <p class="text-xs text-foreground-secondary opacity-70 mt-1">
            {{ t("proxies.detail.lastHeartbeat") }}:
            {{
              data.last_heartbeat
                ? new Date(data.last_heartbeat).toLocaleTimeString()
                : "-"
            }}
          </p>
        </div>
      </div>

      <div class="modal-surface border border-border rounded-xl p-4">
        <h4
          class="text-sm font-semibold text-foreground mb-4 flex items-center gap-2"
        >
          <CpuChipIcon class="w-4 h-4 text-indigo-500" />
          {{ t("proxies.monitoring.systemResources") || "System Resources" }}
        </h4>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <h5 class="text-xs text-foreground-secondary mb-2">
              {{ t("proxies.monitoring.cpuChart") }}
            </h5>
            <div class="h-64">
              <VChart :option="getCPUChartOption()" />
            </div>
          </div>
          <div>
            <h5 class="text-xs text-foreground-secondary mb-2">
              {{ t("proxies.monitoring.memoryChart") }}
            </h5>
            <div class="h-64">
              <VChart :option="getMemoryChartOption()" />
            </div>
          </div>
        </div>
      </div>

      <div class="modal-surface border border-border rounded-xl p-4">
        <div class="flex items-center justify-between mb-4">
          <h4
            class="text-sm font-semibold text-foreground flex items-center gap-2"
          >
            <CircleStackIcon class="w-4 h-4 text-amber-500" />
            {{ t("proxies.monitoring.storageSection") || "Storage" }}
          </h4>
          <select
            v-model="diskIO"
            class="text-sm border border-border rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">{{ t("proxies.monitoring.allDisks") }}</option>
            <option v-for="disk in uniqueDisks" :key="disk" :value="disk">
              {{ disk }}
            </option>
          </select>
        </div>

        <div class="mb-4">
          <h5 class="text-xs text-foreground-secondary mb-2">
            {{ t("proxies.monitoring.diskChart") }}
          </h5>
          <div class="h-56">
            <VChart :option="getDiskChartOption()" />
          </div>
        </div>

        <div v-if="data.disk_io && data.disk_io.length > 0" class="space-y-4">
          <div>
            <h5 class="text-xs text-foreground-secondary mb-2">
              {{
                t("proxies.monitoring.diskUtilAwait") || "Utilization & Await"
              }}
            </h5>
            <div class="h-64">
              <VChart :option="getDiskUtilAwaitChartOption()" />
            </div>
          </div>
          <div>
            <h5 class="text-xs text-foreground-secondary mb-2">
              {{
                t("proxies.monitoring.diskIOPS") ||
                "IOPS (Read/Write per second)"
              }}
            </h5>
            <div class="h-64">
              <VChart :option="getDiskIOPSChartOption()" />
            </div>
          </div>
          <div>
            <h5 class="text-xs text-foreground-secondary mb-2">
              {{
                t("proxies.monitoring.diskBandwidth") ||
                "Bandwidth (Read/Write kB/s)"
              }}
            </h5>
            <div class="h-64">
              <VChart :option="getDiskBandwidthChartOption()" />
            </div>
          </div>
        </div>
      </div>

      <div class="modal-surface border border-border rounded-xl p-4">
        <div class="flex items-center justify-between mb-4">
          <h4
            class="text-sm font-semibold text-foreground flex items-center gap-2"
          >
            <WifiIcon class="w-4 h-4 text-blue-500" />
            {{ t("proxies.monitoring.networkSection") || "Network" }}
          </h4>
          <div
            v-if="data.network_interfaces"
            class="flex items-center gap-3 text-sm"
          >
            <span class="text-foreground-secondary">
              {{ t("proxies.monitoring.total") }}:
            </span>
            <span class="text-purple-700 font-medium">
              ↓ {{ formatBytes(data.network_interfaces.total_bytes_in) }}
            </span>
            <span class="text-cyan-700 font-medium">
              ↑ {{ formatBytes(data.network_interfaces.total_bytes_out) }}
            </span>
          </div>
        </div>

        <div
          v-if="data.network_interfaces?.interfaces?.length > 0"
          class="mb-4 overflow-x-auto"
        >
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-border">
                <th
                  class="text-left py-2 px-3 text-foreground-secondary font-medium"
                >
                  {{ t("proxies.detail.interface") }}
                </th>
                <th
                  class="text-left py-2 px-3 text-foreground-secondary font-medium"
                >
                  {{ t("proxies.monitoring.ipAddress") }}
                </th>
                <th
                  class="text-left py-2 px-3 text-foreground-secondary font-medium"
                >
                  {{ t("proxies.monitoring.macAddress") }}
                </th>
                <th
                  class="text-right py-2 px-3 text-foreground-secondary font-medium"
                >
                  {{ t("proxies.monitoring.bytesIn") }}
                </th>
                <th
                  class="text-right py-2 px-3 text-foreground-secondary font-medium"
                >
                  {{ t("proxies.monitoring.bytesOut") }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(iface, index) in data.network_interfaces.interfaces"
                :key="index"
                class="border-b border-border hover:bg-hover"
              >
                <td class="py-2 px-3 font-medium text-foreground">
                  <div class="flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-green-500"></span>
                    {{ iface.name }}
                  </div>
                </td>
                <td
                  class="py-2 px-3 text-foreground-secondary font-mono text-xs"
                >
                  {{ iface.ip_address || "-" }}
                </td>
                <td
                  class="py-2 px-3 text-foreground-secondary font-mono text-xs"
                >
                  {{ iface.mac_address || "-" }}
                </td>
                <td class="py-2 px-3 text-right text-foreground-secondary">
                  {{ formatBytes(iface.bytes_in) }}
                </td>
                <td class="py-2 px-3 text-right text-foreground-secondary">
                  {{ formatBytes(iface.bytes_out) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div
          v-if="data.network_io && data.network_io.length > 0"
          class="space-y-4"
        >
          <div class="flex items-center justify-end mb-2">
            <select
              v-model="netIOInterface"
              class="text-sm border border-border rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">
                {{ t("proxies.monitoring.allNetInterfaces") }}
              </option>
              <option
                v-for="iface in uniqueNetworkInterfaces"
                :key="iface"
                :value="iface"
              >
                {{ iface }}
              </option>
            </select>
          </div>

          <div>
            <h5 class="text-xs text-foreground-secondary mb-2">
              {{
                t("proxies.monitoring.networkBytes") || "Network Traffic (MB)"
              }}
            </h5>
            <div class="h-64">
              <VChart :option="getNetworkBytesChartOption()" />
            </div>
          </div>

          <div>
            <h5 class="text-xs text-foreground-secondary mb-2">
              {{ t("proxies.monitoring.networkPackets") || "Packets" }}
            </h5>
            <div class="h-64">
              <VChart :option="getNetworkPacketsChartOption()" />
            </div>
          </div>

          <div class="grid grid-cols-4 gap-4">
            <div class="bg-blue-50 rounded-lg p-2">
              <p class="text-xs text-foreground-secondary">
                {{ t("proxies.monitoring.rxPackets") }}
              </p>
              <p class="text-sm font-medium text-blue-700 dark:text-blue-300">
                {{ formatNumber(networkIOStats.rxPackets) }}
              </p>
            </div>
            <div class="bg-green-50 rounded-lg p-2">
              <p class="text-xs text-foreground-secondary">
                {{ t("proxies.monitoring.txPackets") }}
              </p>
              <p class="text-sm font-medium text-green-700">
                {{ formatNumber(networkIOStats.txPackets) }}
              </p>
            </div>
            <div class="bg-red-50 rounded-lg p-2">
              <p class="text-xs text-foreground-secondary">
                {{ t("proxies.monitoring.rxDrop") }}
              </p>
              <p class="text-sm font-medium text-red-700">
                {{ formatNumber(networkIOStats.rxDrop) }}
              </p>
            </div>
            <div class="bg-orange-50 rounded-lg p-2">
              <p class="text-xs text-foreground-secondary">
                {{ t("proxies.monitoring.txErrs") }}
              </p>
              <p class="text-sm font-medium text-orange-700">
                {{ formatNumber(networkIOStats.txErrs) }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
