<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { LineChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import { WifiIcon } from "@heroicons/vue/24/outline";
import GatewayNetworkCharts from "./GatewayNetworkCharts.vue";
import GatewayNetworkInterfaceTable from "./GatewayNetworkInterfaceTable.vue";
import GatewayNetworkStats from "./GatewayNetworkStats.vue";

use([CanvasRenderer, LineChart, TooltipComponent, LegendComponent, GridComponent]);

interface NetworkPoint {
  timestamp: string;
  interface?: string;
  rx_bytes?: number;
  tx_bytes?: number;
  rx_packets?: number;
  tx_packets?: number;
  rx_drop?: number;
  tx_errs?: number;
}

const props = defineProps<{
  current: Record<string, any>;
  networkIo: NetworkPoint[];
  monitoringData: unknown[];
}>();

const { t } = useI18n();
const selectedInterface = ref("");

const interfaces = computed(() => {
  const payload = props.current.network_interfaces;
  if (Array.isArray(payload)) return payload;
  return payload?.interfaces || [];
});

const uniqueInterfaces = computed(() => {
  const names = new Set<string>();
  props.networkIo.forEach((item) => {
    if (item.interface) names.add(item.interface);
  });
  interfaces.value.forEach((item: any) => {
    if (item.name) names.add(item.name);
  });
  return Array.from(names);
});

const filteredNetworkIo = computed(() => {
  if (!selectedInterface.value) return props.networkIo;
  return props.networkIo.filter((item) => item.interface === selectedInterface.value);
});

const networkStats = computed(() => ({
  rxPackets: filteredNetworkIo.value.reduce((sum, item) => sum + (item.rx_packets || 0), 0),
  txPackets: filteredNetworkIo.value.reduce((sum, item) => sum + (item.tx_packets || 0), 0),
  rxDrop: filteredNetworkIo.value.reduce((sum, item) => sum + (item.rx_drop || 0), 0),
  txErrs: filteredNetworkIo.value.reduce((sum, item) => sum + (item.tx_errs || 0), 0),
}));

function formatBytes(bytes?: number | null): string {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatNumber(value?: number | null): string {
  if (!value) return "0";
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(2)}K`;
  return String(value);
}

function formatTime(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString();
}

function sampleTimestamps(timestamps: string[]) {
  if (timestamps.length <= 12) return timestamps;
  const step = Math.ceil(timestamps.length / 12);
  return timestamps.filter((_, index) => index % step === 0);
}

function groupedChartData(rxKey: "rx_bytes" | "rx_packets", txKey: "tx_bytes" | "tx_packets", divisor = 1) {
  const rxGrouped = new Map<string, number>();
  const txGrouped = new Map<string, number>();
  filteredNetworkIo.value.forEach((item) => {
    const ts = item.timestamp;
    rxGrouped.set(ts, (rxGrouped.get(ts) || 0) + ((item[rxKey] as number) || 0));
    txGrouped.set(ts, (txGrouped.get(ts) || 0) + ((item[txKey] as number) || 0));
  });
  const timestamps = sampleTimestamps(
    Array.from(new Set([...rxGrouped.keys(), ...txGrouped.keys()])).sort(),
  );
  return {
    labels: timestamps.map(formatTime),
    rxData: timestamps.map((ts) => (rxGrouped.get(ts) || 0) / divisor),
    txData: timestamps.map((ts) => (txGrouped.get(ts) || 0) / divisor),
  };
}

function dualLineChartOption(options: {
  labels: string[];
  legend: string[];
  series: [string, number[], string][];
  yFormatter: string;
}) {
  return {
    tooltip: { trigger: "axis", axisPointer: { type: "cross" } },
    legend: { data: options.legend, top: 0, textStyle: { fontSize: 10 } },
    grid: { left: "3%", right: "4%", bottom: "3%", containLabel: true, top: "15%" },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: options.labels,
      axisLine: { lineStyle: { color: "#94a3b8" } },
      axisLabel: { color: "#94a3b8", fontSize: 10 },
    },
    yAxis: {
      type: "value",
      min: 0,
      splitLine: { lineStyle: { type: "dashed", color: "#e2e8f0" } },
      axisLabel: { formatter: options.yFormatter, color: "#64748b", fontSize: 10 },
    },
    series: options.series.map(([name, data, color]) => ({
      name,
      type: "line",
      data,
      smooth: true,
      lineStyle: { color },
      areaStyle: {
        color: {
          type: "linear",
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color },
            { offset: 1, color: `${color}05` },
          ],
        },
      },
      symbolSize: 4,
      showSymbol: false,
    })),
  };
}

const networkBytesChartOption = computed(() => {
  const chartData = groupedChartData("rx_bytes", "tx_bytes", 1024 * 1024);
  return dualLineChartOption({
    labels: chartData.labels,
    legend: ["RX Bytes", "TX Bytes"],
    series: [
      ["RX Bytes", chartData.rxData, "#3b82f6"],
      ["TX Bytes", chartData.txData, "#10b981"],
    ],
    yFormatter: "{value} MB",
  });
});

const networkPacketsChartOption = computed(() => {
  const chartData = groupedChartData("rx_packets", "tx_packets");
  return dualLineChartOption({
    labels: chartData.labels,
    legend: ["RX Packets", "TX Packets"],
    series: [
      ["RX Packets", chartData.rxData, "#8b5cf6"],
      ["TX Packets", chartData.txData, "#f59e0b"],
    ],
    yFormatter: "{value}",
  });
});
</script>

<template>
  <div class="modal-surface border border-border rounded-xl p-4">
    <div class="flex items-center justify-between mb-4">
      <h4 class="text-sm font-semibold text-foreground flex items-center gap-2">
        <WifiIcon class="w-4 h-4 text-blue-500" />
        {{ t("gateways.monitoring.networkSection") }}
      </h4>
      <div class="flex items-center gap-3 text-sm">
        <span class="text-foreground-secondary">{{ t("gateways.monitoring.total") }}:</span>
        <span class="text-purple-700 font-medium">
          ↓ {{ formatBytes(current.network_bytes_recv) }}
        </span>
        <span class="text-cyan-700 font-medium">
          ↑ {{ formatBytes(current.network_bytes_sent) }}
        </span>
      </div>
    </div>

    <GatewayNetworkInterfaceTable
      :interfaces="interfaces"
      :format-bytes="formatBytes"
    />

    <div v-if="networkIo.length > 0" class="space-y-4">
      <div class="flex items-center justify-end mb-2">
        <select
          v-model="selectedInterface"
          class="text-sm border border-border rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">{{ t("gateways.monitoring.allNetInterfaces") }}</option>
          <option v-for="iface in uniqueInterfaces" :key="iface" :value="iface">
            {{ iface }}
          </option>
        </select>
      </div>

      <GatewayNetworkCharts
        :network-bytes-chart-option="networkBytesChartOption"
        :network-packets-chart-option="networkPacketsChartOption"
      />
      <GatewayNetworkStats
        :stats="networkStats"
        :format-number="formatNumber"
      />
    </div>
  </div>
</template>
