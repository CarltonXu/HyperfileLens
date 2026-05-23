<script setup lang="ts">
import { ref, toRef } from "vue";
import { useI18n } from "vue-i18n";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { LineChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import VChart from "vue-echarts";
import {
  CircleStackIcon,
  CpuChipIcon,
  ServerStackIcon,
} from "@heroicons/vue/24/outline";
import { useGatewayMonitorCharts } from "../../features/gateways/useGatewayMonitorCharts";

use([
  CanvasRenderer,
  LineChart,
  TooltipComponent,
  LegendComponent,
  GridComponent,
]);

interface HeartbeatData {
  timestamp: string;
  cpu_usage: number | null;
  memory_usage: number | null;
  disk_usage: number | null;
  active_mounts?: number | null;
}

interface DiskIoPoint {
  timestamp: string;
  disk?: string;
  r_s?: number;
  w_s?: number;
  rkB_s?: number;
  wkB_s?: number;
}

const props = defineProps<{
  monitoringData: HeartbeatData[];
  diskIo: DiskIoPoint[];
}>();

const { t } = useI18n();
const selectedDisk = ref("");

const {
  uniqueDisks,
  hasDiskIo,
  cpuChartOption,
  memoryChartOption,
  diskChartOption,
  diskIopsChartOption,
  diskBandwidthChartOption,
  mountChartOption,
} = useGatewayMonitorCharts(
  toRef(props, "monitoringData"),
  toRef(props, "diskIo"),
  selectedDisk,
  t,
);
</script>

<template>
  <div class="space-y-4">
    <div class="modal-surface border border-border rounded-xl p-4">
      <h4
        class="text-sm font-semibold text-foreground mb-4 flex items-center gap-2"
      >
        <CpuChipIcon class="w-4 h-4 text-indigo-500" />
        {{ t("gateways.monitoring.systemResources") }}
      </h4>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <h5 class="text-xs text-foreground-secondary mb-2">
            {{ t("gateways.monitoring.cpuChart") }}
          </h5>
          <div class="h-64">
            <VChart :option="cpuChartOption" />
          </div>
        </div>
        <div>
          <h5 class="text-xs text-foreground-secondary mb-2">
            {{ t("gateways.monitoring.memoryChart") }}
          </h5>
          <div class="h-64">
            <VChart :option="memoryChartOption" />
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
          {{ t("gateways.monitoring.storageSection") }}
        </h4>
        <select
          v-if="uniqueDisks.length > 0"
          v-model="selectedDisk"
          class="text-sm border border-border rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">{{ t("gateways.monitoring.allDisks") }}</option>
          <option v-for="disk in uniqueDisks" :key="disk" :value="disk">
            {{ disk }}
          </option>
        </select>
      </div>

      <div class="mb-4">
        <h5 class="text-xs text-foreground-secondary mb-2">
          {{ t("gateways.monitoring.diskChart") }}
        </h5>
        <div class="h-56">
          <VChart :option="diskChartOption" />
        </div>
      </div>

      <div v-if="hasDiskIo" class="space-y-4">
        <div>
          <h5 class="text-xs text-foreground-secondary mb-2">
            {{ t("gateways.monitoring.diskIOPS") }}
          </h5>
          <div class="h-64">
            <VChart :option="diskIopsChartOption" />
          </div>
        </div>
        <div>
          <h5 class="text-xs text-foreground-secondary mb-2">
            {{ t("gateways.monitoring.diskBandwidth") }}
          </h5>
          <div class="h-64">
            <VChart :option="diskBandwidthChartOption" />
          </div>
        </div>
      </div>
    </div>

    <div class="modal-surface border border-border rounded-xl p-4">
      <h4
        class="text-sm font-semibold text-foreground mb-4 flex items-center gap-2"
      >
        <ServerStackIcon class="w-4 h-4 text-amber-500" />
        {{ t("gateways.monitoring.mountsChart") }}
      </h4>
      <div class="h-56">
        <VChart :option="mountChartOption" />
      </div>
    </div>
  </div>
</template>
