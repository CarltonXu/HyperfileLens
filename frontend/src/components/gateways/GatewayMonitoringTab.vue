<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import { ArrowPathIcon, ClockIcon } from "@heroicons/vue/24/outline";
import GatewayMonitoringSummary from "./GatewayMonitoringSummary.vue";
import GatewayMonitoringCharts from "./GatewayMonitoringCharts.vue";
import GatewayMonitoringNetwork from "./GatewayMonitoringNetwork.vue";
import GatewayHeartbeatTable from "./GatewayHeartbeatTable.vue";

interface HeartbeatData {
  timestamp: string;
  cpu_usage: number | null;
  memory_usage: number | null;
  disk_usage: number | null;
  active_mounts: number;
  network_bytes_sent?: number;
  network_bytes_recv?: number;
  network_packets_sent?: number;
  network_packets_recv?: number;
  memory_total?: number;
  disk_total?: number;
  cpu_cores?: number;
  load_average?: number[];
  process_count?: number;
  network_interfaces?: any;
  disk_io?: any[];
}

interface Gateway {
  id: string;
  name: string;
  last_heartbeat?: string;
}

const props = defineProps<{
  gateway: Gateway;
  current: Record<string, any> | null;
  networkIo: any[];
  diskIo: any[];
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

const emit = defineEmits<{
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

const latestCurrent = computed(() => {
  if (props.current) return props.current;
  const last = props.monitoringData[props.monitoringData.length - 1];
  return last || {};
});
</script>

<template>
  <div class="space-y-4">
    <div
      class="flex items-center justify-between bg-background-secondary rounded-xl p-3"
    >
      <div class="flex items-center gap-2">
        <ClockIcon class="w-4 h-4 text-foreground-secondary" />
        <span class="text-sm font-medium text-foreground">
          {{ t("gateways.monitoring.title") }}
        </span>
      </div>
      <div class="flex items-center gap-2">
        <select
          :value="timeRange"
          @change="
            emit(
              'update:timeRange',
              Number(($event.target as HTMLSelectElement).value),
            )
          "
          class="text-sm bg-background text-foreground border border-border rounded-lg px-2 py-1 focus:outline-none focus:ring-2 focus:ring-indigo-500"
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
          @click="emit('refresh')"
          class="p-1.5 text-foreground-secondary hover:text-indigo-600 hover:bg-card rounded-lg"
          :title="t('common.refresh')"
        >
          <ArrowPathIcon class="w-4 h-4" />
        </button>
      </div>
    </div>

    <div v-if="isLoading" class="flex items-center justify-center py-12">
      <ArrowPathIcon class="w-6 h-6 text-indigo-500 animate-spin" />
    </div>

    <div v-else-if="monitoringData.length === 0" class="text-center py-12">
      <p class="text-foreground-secondary">
        {{ t("gateways.monitoring.empty") }}
      </p>
    </div>

    <template v-else>
      <GatewayMonitoringSummary
        :gateway="gateway"
        :current="latestCurrent"
        :stats="stats"
      />
      <GatewayMonitoringCharts
        :monitoring-data="monitoringData"
        :disk-io="diskIo"
      />
      <GatewayMonitoringNetwork
        :current="latestCurrent"
        :network-io="networkIo"
        :monitoring-data="monitoringData"
      />
      <GatewayHeartbeatTable :heartbeats="monitoringData" />
    </template>
  </div>
</template>
