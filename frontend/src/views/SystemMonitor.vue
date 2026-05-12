<script setup lang="ts">
import { computed, onMounted, ref, onUnmounted, nextTick } from "vue";
import { useI18n } from "vue-i18n";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { LineChart, BarChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import VChart from "vue-echarts";
import {
  ArrowPathIcon,
  ClockIcon,
  CpuChipIcon,
  CircleStackIcon,
  Squares2X2Icon,
  WifiIcon,
  ServerIcon,
  ChevronDownIcon,
} from "@heroicons/vue/24/outline";
import { alertsApi } from "@/api";

use([
  CanvasRenderer,
  LineChart,
  BarChart,
  GridComponent,
  LegendComponent,
  TooltipComponent,
]);

const { t } = useI18n();
const loading = ref(false);

// Time range selection - new design
const showTimeDropdown = ref(false);
const timeDropdownButtonRef = ref<HTMLElement | null>(null);
const timeDropdownStyle = ref<Record<string, string>>({});
const selectedTimeOption = ref<string>("24h");
const customTimeRange = ref<{ start: string; end: string }>({
  start: "",
  end: "",
});

// Time preset options
const timePresets = [
  {
    value: "5m",
    label: t("proxies.monitoring.last5m") || "Last 5 minutes",
    hours: 5 / 60,
  },
  {
    value: "15m",
    label: t("proxies.monitoring.last15m") || "Last 15 minutes",
    hours: 15 / 60,
  },
  {
    value: "30m",
    label: t("proxies.monitoring.last30m") || "Last 30 minutes",
    hours: 30 / 60,
  },
  {
    value: "1h",
    label: t("proxies.monitoring.last1h") || "Last 1 hour",
    hours: 1,
  },
  {
    value: "3h",
    label: t("proxies.monitoring.last3h") || "Last 3 hours",
    hours: 3,
  },
  {
    value: "6h",
    label: t("proxies.monitoring.last6h") || "Last 6 hours",
    hours: 6,
  },
  {
    value: "12h",
    label: t("proxies.monitoring.last12h") || "Last 12 hours",
    hours: 12,
  },
  {
    value: "24h",
    label: t("proxies.monitoring.last24h") || "Last 24 hours",
    hours: 24,
  },
  {
    value: "2d",
    label: t("proxies.monitoring.last2d") || "Last 2 days",
    hours: 48,
  },
  {
    value: "7d",
    label: t("proxies.monitoring.last7d") || "Last 7 days",
    hours: 168,
  },
  {
    value: "15d",
    label: t("proxies.monitoring.last15d") || "Last 15 days",
    hours: 360,
  },
  {
    value: "30d",
    label: t("proxies.monitoring.last30d") || "Last 30 days",
    hours: 720,
  },
];

const data = ref<any>({ host: {}, current: {}, series: [] });

// Auto refresh
const autoRefresh = ref({
  enabled: false,
  interval: 30,
  timer: null as number | null,
});

// Disk and network interface selectors
const selectedDisk = ref<string>("all");
const selectedNetwork = ref<string>("all");

// Format date to ISO string (UTC)
function formatToUTC(date: Date): string {
  return date.toISOString();
}

async function fetchData(hours?: number, silent = false) {
  if (!silent) loading.value = true;
  try {
    let params: any = {};

    if (hours !== undefined) {
      // Use hours for preset time ranges (calculate start_at and end_at)
      const now = new Date();
      const start = new Date(now.getTime() - hours * 60 * 60 * 1000);
      params.start_at = formatToUTC(start);
      params.end_at = formatToUTC(now);
      console.log(
        `Fetching system metrics for ${hours} hours: ${params.start_at} to ${params.end_at}`,
      );
    }

    const res = await alertsApi.systemMonitor(params);
    data.value = res.data;
    console.log(`Received ${res.data.series?.length || 0} data points`);
  } catch (error) {
    console.error("Failed to fetch system metrics:", error);
  } finally {
    if (!silent) loading.value = false;
  }
}

function selectTimePreset(value: string) {
  selectedTimeOption.value = value;
  const preset = timePresets.find((p) => p.value === value);
  if (preset) {
    fetchData(preset.hours);
  }
  showTimeDropdown.value = false;
}

function updateTimeDropdownPosition() {
  const button = timeDropdownButtonRef.value;
  if (!button) return;

  const rect = button.getBoundingClientRect();
  const width = Math.min(600, window.innerWidth - 32);
  const left = Math.max(
    16,
    Math.min(rect.right - width, window.innerWidth - width - 16),
  );

  timeDropdownStyle.value = {
    position: "fixed",
    top: `${rect.bottom + 8}px`,
    left: `${left}px`,
    width: `${width}px`,
    maxWidth: "calc(100vw - 2rem)",
  };
}

async function toggleTimeDropdown() {
  showTimeDropdown.value = !showTimeDropdown.value;
  if (showTimeDropdown.value) {
    await nextTick();
    updateTimeDropdownPosition();
  }
}

function closeTimeDropdown() {
  showTimeDropdown.value = false;
}

function handleTimeDropdownViewportChange() {
  if (showTimeDropdown.value) updateTimeDropdownPosition();
}

async function applyCustomTimeRange() {
  if (customTimeRange.value.start && customTimeRange.value.end) {
    const start = new Date(customTimeRange.value.start);
    const end = new Date(customTimeRange.value.end);
    if (!isNaN(start.getTime()) && !isNaN(end.getTime())) {
      selectedTimeOption.value = "custom";
      const params = {
        start_at: formatToUTC(start),
        end_at: formatToUTC(end),
      };
      loading.value = true;
      try {
        const res = await alertsApi.systemMonitor(params);
        data.value = res.data;
        console.log(
          `Received ${res.data.series?.length || 0} data points for custom range`,
        );
      } catch (err) {
        console.error("Failed to fetch system metrics:", err);
      } finally {
        loading.value = false;
      }
      showTimeDropdown.value = false;
    }
  }
}

function setAutoRefresh(interval: number) {
  // Clear existing timer
  if (autoRefresh.value.timer) {
    clearInterval(autoRefresh.value.timer);
    autoRefresh.value.timer = null;
  }

  autoRefresh.value.enabled = interval > 0;
  autoRefresh.value.interval = interval;

  if (interval > 0) {
    autoRefresh.value.timer = window.setInterval(() => {
      // Silent refresh using the same time range
      if (selectedTimeOption.value !== "custom") {
        const preset = timePresets.find(
          (p) => p.value === selectedTimeOption.value,
        );
        if (preset) {
          fetchData(preset.hours, true);
        }
      } else {
        // Refresh with custom time range
        const start = new Date(customTimeRange.value.start);
        const end = new Date(customTimeRange.value.end);
        if (!isNaN(start.getTime()) && !isNaN(end.getTime())) {
          const params = {
            start_at: formatToUTC(start),
            end_at: formatToUTC(end),
          };
          alertsApi
            .systemMonitor(params)
            .then((res) => {
              data.value = res.data;
            })
            .catch((err) => {
              console.error("Failed to refresh system metrics:", err);
            });
        }
      }
    }, interval * 1000);
  }
}

const labels = computed(() =>
  data.value.series.map((item: any) =>
    new Date(item.timestamp).toLocaleTimeString(),
  ),
);
const current = computed(() => data.value.current || {});
const currentDisks = computed(() => current.value.disks || []);
const currentNetworks = computed(() => current.value.networks || []);

// Get unique disk names from the data
const uniqueDiskNames = computed(() => {
  const names = new Set<string>();
  data.value.series.forEach((sample: any) => {
    if (sample.disks) {
      sample.disks.forEach((disk: any) => {
        names.add(disk.mountpoint || disk.device);
      });
    }
  });
  return Array.from(names).sort();
});

// Get unique network interface names from the data
const uniqueNetworkNames = computed(() => {
  const names = new Set<string>();
  data.value.series.forEach((sample: any) => {
    if (sample.networks) {
      sample.networks.forEach((nic: any) => names.add(nic.name));
    }
  });
  return Array.from(names).sort();
});

// Filter disks based on selection
const filteredDisks = computed(() => {
  if (selectedDisk.value === "all") return currentDisks.value;
  return currentDisks.value.filter(
    (d: any) =>
      d.mountpoint === selectedDisk.value || d.device === selectedDisk.value,
  );
});

// Filter networks based on selection
const filteredNetworks = computed(() => {
  if (selectedNetwork.value === "all") return currentNetworks.value;
  return currentNetworks.value.filter(
    (n: any) => n.name === selectedNetwork.value,
  );
});

// Calculate total disk usage (sum of all disks)
const totalDiskUsage = computed(() => {
  const disks = currentDisks.value;
  if (disks.length === 0) return { used: 0, total: 0, percent: 0 };
  const used = disks.reduce((sum: number, d: any) => sum + (d.used || 0), 0);
  const total = disks.reduce((sum: number, d: any) => sum + (d.total || 0), 0);
  return {
    used,
    total,
    percent: total > 0 ? Math.round((used / total) * 100) : 0,
  };
});

function bytes(value: number) {
  if (!value) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let index = 0;
  let size = value;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(size >= 10 ? 1 : 2)} ${units[index]}`;
}

function lineOption(title: string, series: any[], max?: number) {
  return {
    color: [
      "#6366f1",
      "#10b981",
      "#f59e0b",
      "#ef4444",
      "#06b6d4",
      "#8b5cf6",
      "#84cc16",
      "#f97316",
    ],
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(24,24,27,.94)",
      borderWidth: 0,
      textStyle: { color: "#fff" },
    },
    legend: { top: 0, type: "scroll" },
    grid: { left: 46, right: 18, top: 42, bottom: 30 },
    xAxis: {
      type: "category",
      data: labels.value,
      boundaryGap: false,
      axisLine: { lineStyle: { color: "#71717a" } },
    },
    yAxis: {
      type: "value",
      max,
      axisLine: { lineStyle: { color: "#71717a" } },
      splitLine: { lineStyle: { color: "rgba(113,113,122,.22)" } },
    },
    series: series.map((item) => ({
      name: item.name || title,
      type: "line",
      smooth: true,
      showSymbol: false,
      lineStyle: { width: 2 },
      areaStyle: { opacity: 0.08 },
      data: item.data,
    })),
  };
}

function diffSeries(items: any[], key: string, field: string) {
  const names = new Set<string>();
  items.forEach((sample) =>
    (sample[key] || []).forEach((row: any) =>
      names.add(row.name || row.mountpoint || row.device),
    ),
  );
  return Array.from(names).map((name) => {
    let prev: number | null = null;
    return {
      name,
      data: items.map((sample) => {
        const row = (sample[key] || []).find(
          (item: any) => (item.name || item.mountpoint || item.device) === name,
        );
        const value = row?.[field] || 0;
        const rate = prev === null ? 0 : Math.max(value - prev, 0);
        prev = value;
        return rate;
      }),
    };
  });
}

const cpuOption = computed(() =>
  lineOption(
    t("alertsPage.monitor.cpuUsage"),
    [
      {
        name: t("alertsPage.monitor.cpuUsage"),
        data: data.value.series.map(
          (item: any) => item.cpu?.usage_percent || 0,
        ),
      },
    ],
    100,
  ),
);
const loadOption = computed(() =>
  lineOption(t("alertsPage.monitor.loadAverage"), [
    {
      name: "1m",
      data: data.value.series.map((item: any) => item.load_average?.[0] || 0),
    },
    {
      name: "5m",
      data: data.value.series.map((item: any) => item.load_average?.[1] || 0),
    },
    {
      name: "15m",
      data: data.value.series.map((item: any) => item.load_average?.[2] || 0),
    },
  ]),
);
const memoryOption = computed(() =>
  lineOption(
    t("alertsPage.monitor.memoryUsage"),
    [
      {
        name: t("alertsPage.monitor.memoryUsage"),
        data: data.value.series.map((item: any) => item.memory?.percent || 0),
      },
      {
        name: "Swap",
        data: data.value.series.map((item: any) => item.swap?.percent || 0),
      },
    ],
    100,
  ),
);
const diskUsageOption = computed(() => {
  // Build series based on selection
  let series: any[] = [];

  if (selectedDisk.value === "all") {
    // Calculate total disk usage for each timestamp
    const totalData = data.value.series.map((sample: any) => {
      const disks = sample.disks || [];
      if (disks.length === 0) return 0;
      const used = disks.reduce(
        (sum: number, d: any) => sum + (d.used || 0),
        0,
      );
      const total = disks.reduce(
        (sum: number, d: any) => sum + (d.total || 0),
        0,
      );
      return total > 0 ? Math.round((used / total) * 100) : 0;
    });
    series = [{ name: t("common.total"), data: totalData }];
  } else {
    // Show specific disk
    series = [
      {
        name: selectedDisk.value,
        data: data.value.series.map((sample: any) => {
          const disks = sample.disks || [];
          const disk = disks.find(
            (d: any) =>
              d.mountpoint === selectedDisk.value ||
              d.device === selectedDisk.value,
          );
          return disk?.percent || 0;
        }),
      },
    ];
  }

  return lineOption(t("alertsPage.monitor.diskUsage"), series, 100);
});
const diskThroughputOption = computed(() => {
  let series: any[] = [];
  const allSeries = [
    ...diffSeries(data.value.series, "disk_io", "read_bytes").map((item) => ({
      name: `${item.name} read`,
      data: item.data.map((value: number) => Math.round(value / 1024)),
    })),
    ...diffSeries(data.value.series, "disk_io", "write_bytes").map((item) => ({
      name: `${item.name} write`,
      data: item.data.map((value: number) => Math.round(value / 1024)),
    })),
  ];

  if (selectedDisk.value === "all") {
    series = allSeries;
  } else {
    series = allSeries.filter((s) => s.name.startsWith(selectedDisk.value));
  }

  return lineOption(t("alertsPage.monitor.diskThroughput"), series);
});
const diskIopsOption = computed(() => {
  let series: any[] = [];
  const allSeries = [
    ...diffSeries(data.value.series, "disk_io", "read_count").map((item) => ({
      name: `${item.name} read`,
      data: item.data,
    })),
    ...diffSeries(data.value.series, "disk_io", "write_count").map((item) => ({
      name: `${item.name} write`,
      data: item.data,
    })),
  ];

  if (selectedDisk.value === "all") {
    series = allSeries;
  } else {
    series = allSeries.filter((s) => s.name.startsWith(selectedDisk.value));
  }

  return lineOption(t("alertsPage.monitor.diskIops"), series);
});
const networkBytesOption = computed(() => {
  let series: any[] = [];
  const allSeries = [
    ...diffSeries(data.value.series, "networks", "bytes_recv").map((item) => ({
      name: `${item.name} in`,
      data: item.data.map((value: number) => Math.round(value / 1024)),
    })),
    ...diffSeries(data.value.series, "networks", "bytes_sent").map((item) => ({
      name: `${item.name} out`,
      data: item.data.map((value: number) => Math.round(value / 1024)),
    })),
  ];

  if (selectedNetwork.value === "all") {
    series = allSeries;
  } else {
    series = allSeries.filter((s) => s.name.startsWith(selectedNetwork.value));
  }

  return lineOption(t("alertsPage.monitor.networkTraffic"), series);
});
const networkPacketsOption = computed(() => {
  let series: any[] = [];
  const allSeries = [
    ...diffSeries(data.value.series, "networks", "packets_recv").map(
      (item) => ({ name: `${item.name} in`, data: item.data }),
    ),
    ...diffSeries(data.value.series, "networks", "packets_sent").map(
      (item) => ({ name: `${item.name} out`, data: item.data }),
    ),
  ];

  if (selectedNetwork.value === "all") {
    series = allSeries;
  } else {
    series = allSeries.filter((s) => s.name.startsWith(selectedNetwork.value));
  }

  return lineOption(t("alertsPage.monitor.networkPackets"), series);
});

onMounted(() => {
  // Initialize default custom time range
  const now = new Date();
  const start = new Date(now.getTime() - 24 * 60 * 60 * 1000);
  const formatDateTime = (date: Date) => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    const hours = String(date.getHours()).padStart(2, "0");
    const minutes = String(date.getMinutes()).padStart(2, "0");
    return `${year}-${month}-${day}T${hours}:${minutes}`;
  };
  customTimeRange.value = {
    start: formatDateTime(start),
    end: formatDateTime(now),
  };
  window.addEventListener("resize", handleTimeDropdownViewportChange);
  window.addEventListener("scroll", handleTimeDropdownViewportChange, true);
  // Fetch initial data
  fetchData(24);
});

// Cleanup on unmount
onUnmounted(() => {
  if (autoRefresh.value.timer) {
    clearInterval(autoRefresh.value.timer);
  }
  window.removeEventListener("resize", handleTimeDropdownViewportChange);
  window.removeEventListener("scroll", handleTimeDropdownViewportChange, true);
});
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div
      class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-foreground">
          {{ t("alertsPage.tabs.monitor") }}
        </h1>
        <p class="mt-1 text-sm text-foreground-secondary">
          {{ data.host.hostname || "-" }} ·
          {{ data.host.platform || t("alertsPage.monitor.subtitle") }}
        </p>
      </div>
      <div class="flex items-center gap-2 flex-wrap">
        <!-- Time Range Selector -->
        <div class="relative">
          <button
            ref="timeDropdownButtonRef"
            @click="toggleTimeDropdown"
            data-time-dropdown-button
            class="flex items-center gap-2 px-4 py-2 text-sm font-medium text-foreground bg-card border border-border rounded-lg hover:border-indigo-500 transition-colors">
            <ClockIcon class="w-4 h-4" />
            <span>{{
              timePresets.find((p) => p.value === selectedTimeOption)?.label ||
              t("proxies.monitoring.selectTimeRange")
            }}</span>
            <ChevronDownIcon class="w-4 h-4" />
          </button>
        </div>

        <Teleport to="body">
          <!-- Click outside to close dropdown -->
          <div
            v-if="showTimeDropdown"
            @click="closeTimeDropdown"
            class="fixed inset-0 z-[2147483646]"></div>

          <!-- Time Dropdown Panel -->
          <div
            v-if="showTimeDropdown"
            class="z-[2147483647] popover-surface border border-border rounded-xl shadow-2xl max-w-[calc(100vw-2rem)]"
            :style="timeDropdownStyle"
            @click.stop>
            <div class="flex h-[400px] overflow-hidden">
              <!-- Left: Presets -->
              <div class="w-1/2 border-r border-border flex flex-col min-h-0">
                <div class="px-4 pt-4 pb-3 bg-card border-b border-border/60">
                  <p class="text-xs font-medium text-foreground-secondary">
                    {{ t("proxies.monitoring.quickSelect") }}
                  </p>
                </div>
                <div class="relative flex-1 min-h-0">
                  <div class="h-full overflow-y-auto p-4 pb-8 space-y-1">
                    <button
                      v-for="preset in timePresets"
                      :key="preset.value"
                      @click="selectTimePreset(preset.value)"
                      :class="[
                        'w-full text-left px-3 py-2 text-sm rounded-lg transition-colors',
                        selectedTimeOption === preset.value
                          ? 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 font-medium'
                          : 'text-foreground-secondary hover:bg-hover',
                      ]">
                      {{ preset.label }}
                    </button>
                  </div>
                  <div
                    class="pointer-events-none absolute inset-x-0 bottom-0 h-5 bg-gradient-to-t from-card to-transparent" />
                </div>
              </div>

              <!-- Right: Custom Date Range -->
              <div class="w-1/2 flex flex-col min-h-0">
                <div class="px-4 pt-4 pb-3 bg-card border-b border-border/60">
                  <p class="text-xs font-medium text-foreground-secondary">
                    {{ t("proxies.monitoring.customTimeRange") }}
                  </p>
                </div>
                <div class="relative flex-1 min-h-0">
                  <div class="h-full overflow-y-auto p-4 pb-8 space-y-3">
                    <div>
                      <label
                        class="block text-xs text-foreground-secondary mb-1.5"
                        >{{ t("proxies.monitoring.startTime") }}</label
                      >
                      <div class="relative">
                        <input
                          v-model="customTimeRange.start"
                          type="datetime-local"
                          class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-indigo-500 cursor-pointer" />
                      </div>
                    </div>
                    <div>
                      <label
                        class="block text-xs text-foreground-secondary mb-1.5"
                        >{{ t("proxies.monitoring.endTime") }}</label
                      >
                      <div class="relative">
                        <input
                          v-model="customTimeRange.end"
                          type="datetime-local"
                          class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-indigo-500 cursor-pointer" />
                      </div>
                    </div>
                    <button
                      @click="applyCustomTimeRange"
                      :disabled="!customTimeRange.start || !customTimeRange.end"
                      class="w-full px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                      {{ t("proxies.detail.apply") }}
                    </button>
                  </div>
                  <div
                    class="pointer-events-none absolute inset-x-0 bottom-0 h-5 bg-gradient-to-t from-card to-transparent" />
                </div>
              </div>
            </div>
          </div>
        </Teleport>

        <!-- Auto Refresh -->
        <div class="flex items-center gap-2">
          <div class="flex items-center gap-2 border rounded-lg p-1">
            <ClockIcon class="w-3.5 h-3.5 text-foreground-muted ml-2" />
            <select
              :value="autoRefresh.enabled ? autoRefresh.interval : 0"
              @change="
                setAutoRefresh(
                  Number(($event.target as HTMLSelectElement).value),
                )
              "
              class="px-3 py-1.5 text-sm font-medium rounded-md transition-colors bg-transparent text-foreground focus:outline-none cursor-pointer">
              <option :value="0">
                {{ t("proxies.monitoring.refreshOff") }}
              </option>
              <option :value="10">
                {{ t("proxies.monitoring.refresh10s") }}
              </option>
              <option :value="30">
                {{ t("proxies.monitoring.refresh30s") }}
              </option>
              <option :value="60">
                {{ t("proxies.monitoring.refresh1m") }}
              </option>
              <option :value="300">
                {{ t("proxies.monitoring.refresh5m") }}
              </option>
            </select>
          </div>
        </div>

        <!-- Refresh Button -->
        <button
          @click="fetchData()"
          :disabled="loading"
          class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
          <ArrowPathIcon :class="['w-4 h-4', loading && 'animate-spin']" />
          {{ t("common.refresh") }}
        </button>
      </div>
    </div>

    <!-- System Resource Cards -->
    <div class="grid grid-cols-2 lg:grid-cols-5 gap-4">
      <!-- CPU -->
      <div class="bg-card border border-border rounded-xl p-4">
        <div class="flex items-center gap-2">
          <div
            class="w-8 h-8 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center">
            <CpuChipIcon class="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
          </div>
          <p class="text-sm text-foreground-secondary">
            {{ t("proxies.monitoring.cpu") }}
          </p>
        </div>
        <p class="mt-3 text-2xl font-semibold text-foreground">
          {{ current.cpu?.usage_percent || 0 }}%
        </p>
        <p class="text-xs text-foreground-muted mt-1">
          {{ current.cpu?.logical_cores || "-" }}
          {{ t("proxies.detail.cores") }}
        </p>
      </div>

      <!-- Memory -->
      <div class="bg-card border border-border rounded-xl p-4">
        <div class="flex items-center gap-2">
          <div
            class="w-8 h-8 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
            <CircleStackIcon
              class="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          </div>
          <p class="text-sm text-foreground-secondary">
            {{ t("alertsPage.monitor.memoryUsage") }}
          </p>
        </div>
        <p class="mt-3 text-2xl font-semibold text-foreground">
          {{ current.memory?.percent || 0 }}%
        </p>
        <p class="text-xs text-foreground-muted mt-1">
          {{ bytes(current.memory?.used) }} / {{ bytes(current.memory?.total) }}
        </p>
      </div>

      <!-- Swap -->
      <div class="bg-card border border-border rounded-xl p-4">
        <div class="flex items-center gap-2">
          <div
            class="w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
            <CircleStackIcon class="w-4 h-4 text-blue-600 dark:text-blue-400" />
          </div>
          <p class="text-sm text-foreground-secondary">
            {{ t("alertsPage.monitor.swapUsage") }}
          </p>
        </div>
        <p class="mt-3 text-2xl font-semibold text-foreground">
          {{ current.swap?.percent || 0 }}%
        </p>
        <p class="text-xs text-foreground-muted mt-1">
          {{ bytes(current.swap?.used) }} / {{ bytes(current.swap?.total) }}
        </p>
      </div>

      <!-- Disk -->
      <div class="bg-card border border-border rounded-xl p-4">
        <div class="flex items-center gap-2">
          <div
            class="w-8 h-8 rounded-lg bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
            <Squares2X2Icon
              class="w-4 h-4 text-amber-600 dark:text-amber-400" />
          </div>
          <p class="text-sm text-foreground-secondary">
            {{ t("alertsPage.monitor.diskUsage") }}
          </p>
        </div>
        <p class="mt-3 text-2xl font-semibold text-foreground">
          {{ totalDiskUsage.percent }}%
        </p>
        <p class="text-xs text-foreground-muted mt-1">
          {{ bytes(totalDiskUsage.used) }} / {{ bytes(totalDiskUsage.total) }}
        </p>
      </div>

      <!-- Network -->
      <div class="bg-card border border-border rounded-xl p-4">
        <div class="flex items-center gap-2">
          <div
            class="w-8 h-8 rounded-lg bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
            <WifiIcon class="w-4 h-4 text-purple-600 dark:text-purple-400" />
          </div>
          <p class="text-sm text-foreground-secondary">
            {{ t("alertsPage.monitor.networkInterfaces") }}
          </p>
        </div>
        <p class="mt-3 text-2xl font-semibold text-foreground">
          {{ currentNetworks.length }}
        </p>
        <p class="text-sm text-foreground-muted mt-1">
          {{ t("proxies.monitoring.networkInterfaces") }}
        </p>
      </div>
    </div>

    <!-- System Resources Charts -->
    <div>
      <div class="flex items-center gap-2 mb-4">
        <div
          class="w-8 h-8 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center">
          <ServerIcon class="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
        </div>
        <h2 class="text-lg font-semibold text-foreground">
          {{ t("proxies.monitoring.systemResources") }}
        </h2>
      </div>
      <div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div class="bg-card border border-border rounded-xl p-5 shadow-sm">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-sm font-medium text-foreground">
              {{ t("alertsPage.monitor.cpuUsage") }}
            </h3>
            <CpuChipIcon class="w-4 h-4 text-indigo-500" />
          </div>
          <VChart class="h-72" :option="cpuOption" autoresize />
        </div>
        <div class="bg-card border border-border rounded-xl p-5 shadow-sm">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-sm font-medium text-foreground">
              {{ t("alertsPage.monitor.loadAverage") }}
            </h3>
            <ServerIcon class="w-4 h-4 text-amber-500" />
          </div>
          <VChart class="h-72" :option="loadOption" autoresize />
        </div>
        <div class="bg-card border border-border rounded-xl p-5 shadow-sm">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-sm font-medium text-foreground">
              {{ t("alertsPage.monitor.memoryUsage") }}
            </h3>
            <CircleStackIcon class="w-4 h-4 text-emerald-500" />
          </div>
          <VChart class="h-72" :option="memoryOption" autoresize />
        </div>
        <div class="bg-card border border-border rounded-xl p-5 shadow-sm">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-sm font-medium text-foreground">
              {{ t("alertsPage.monitor.diskUsage") }}
            </h3>
            <Squares2X2Icon class="w-4 h-4 text-amber-500" />
          </div>
          <VChart class="h-72" :option="diskUsageOption" autoresize />
        </div>
      </div>
    </div>

    <!-- Storage Section -->
    <div>
      <div class="flex items-center justify-between gap-2 mb-4">
        <div class="flex items-center gap-2">
          <div
            class="w-8 h-8 rounded-lg bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
            <Squares2X2Icon
              class="w-4 h-4 text-amber-600 dark:text-amber-400" />
          </div>
          <h2 class="text-lg font-semibold text-foreground">
            {{ t("proxies.monitoring.storageSection") }}
          </h2>
        </div>
        <!-- Disk Selector -->
        <div v-if="uniqueDiskNames.length > 0" class="flex items-center gap-2">
          <select
            v-model="selectedDisk"
            class="px-3 py-1.5 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-amber-500">
            <option value="all">{{ t("proxies.monitoring.all") }}</option>
            <option v-for="name in uniqueDiskNames" :key="name" :value="name">
              {{ name }}
            </option>
          </select>
        </div>
      </div>
      <div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div class="bg-card border border-border rounded-xl p-5 shadow-sm">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-sm font-medium text-foreground">
              {{ t("alertsPage.monitor.diskThroughput") }}
            </h3>
            <Squares2X2Icon class="w-4 h-4 text-amber-500" />
          </div>
          <VChart class="h-72" :option="diskThroughputOption" autoresize />
        </div>
        <div class="bg-card border border-border rounded-xl p-5 shadow-sm">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-sm font-medium text-foreground">
              {{ t("alertsPage.monitor.diskIops") }}
            </h3>
            <Squares2X2Icon class="w-4 h-4 text-amber-500" />
          </div>
          <VChart class="h-72" :option="diskIopsOption" autoresize />
        </div>
      </div>
    </div>

    <!-- Network Section -->
    <div>
      <div class="flex items-center justify-between gap-2 mb-4">
        <div class="flex items-center gap-2">
          <div
            class="w-8 h-8 rounded-lg bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
            <WifiIcon class="w-4 h-4 text-purple-600 dark:text-purple-400" />
          </div>
          <h2 class="text-lg font-semibold text-foreground">
            {{ t("proxies.monitoring.networkSection") }}
          </h2>
        </div>
        <!-- Network Interface Selector -->
        <div
          v-if="uniqueNetworkNames.length > 0"
          class="flex items-center gap-2">
          <select
            v-model="selectedNetwork"
            class="px-3 py-1.5 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-purple-500">
            <option value="all">{{ t("proxies.monitoring.all") }}</option>
            <option
              v-for="name in uniqueNetworkNames"
              :key="name"
              :value="name">
              {{ name }}
            </option>
          </select>
        </div>
      </div>
      <div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div class="bg-card border border-border rounded-xl p-5 shadow-sm">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-sm font-medium text-foreground">
              {{ t("alertsPage.monitor.networkTraffic") }}
            </h3>
            <WifiIcon class="w-4 h-4 text-purple-500" />
          </div>
          <VChart class="h-72" :option="networkBytesOption" autoresize />
        </div>
        <div class="bg-card border border-border rounded-xl p-5 shadow-sm">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-sm font-medium text-foreground">
              {{ t("alertsPage.monitor.networkPackets") }}
            </h3>
            <WifiIcon class="w-4 h-4 text-purple-500" />
          </div>
          <VChart class="h-72" :option="networkPacketsOption" autoresize />
        </div>
      </div>
    </div>

    <!-- Disk Details -->
    <div class="bg-card border border-border rounded-xl overflow-hidden">
      <div class="p-4 border-b border-border flex items-center gap-3">
        <div
          class="w-8 h-8 rounded-lg bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
          <Squares2X2Icon class="w-4 h-4 text-amber-600 dark:text-amber-400" />
        </div>
        <h2 class="text-base font-semibold text-foreground">
          {{ t("proxies.monitoring.storageSection") }}
        </h2>
        <span class="text-xs text-foreground-muted"
          >({{ filteredDisks.length }} / {{ currentDisks.length }}
          {{ t("proxies.detail.total") }})</span
        >
      </div>
      <div class="divide-y divide-border">
        <div
          v-for="disk in filteredDisks"
          :key="disk.mountpoint"
          class="p-4 hover:bg-hover transition-colors">
          <div class="flex justify-between items-center">
            <div class="flex items-center gap-3">
              <Squares2X2Icon class="w-5 h-5 text-amber-500" />
              <span class="text-sm font-medium text-foreground">{{
                disk.mountpoint
              }}</span>
              <span class="text-xs text-foreground-muted">{{
                disk.device
              }}</span>
            </div>
            <span class="text-sm text-foreground-secondary"
              >{{ disk.percent }}%</span
            >
          </div>
          <div
            class="mt-3 h-2 rounded-full bg-background-tertiary overflow-hidden">
            <div
              class="h-full transition-all duration-300"
              :class="
                disk.percent > 90
                  ? 'bg-red-500'
                  : disk.percent > 75
                    ? 'bg-amber-500'
                    : 'bg-indigo-500'
              "
              :style="{ width: `${disk.percent || 0}%` }" />
          </div>
          <p class="mt-2 text-xs text-foreground-muted flex items-center gap-2">
            <span>{{ bytes(disk.used) }} / {{ bytes(disk.total) }}</span>
            <span>·</span>
            <span
              >{{ bytes(disk.free) }} {{ t("proxies.detail.available") }}</span
            >
          </p>
        </div>
      </div>
    </div>

    <!-- Network Details -->
    <div class="bg-card border border-border rounded-xl overflow-hidden">
      <div class="p-4 border-b border-border flex items-center gap-3">
        <div
          class="w-8 h-8 rounded-lg bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
          <WifiIcon class="w-4 h-4 text-purple-600 dark:text-purple-400" />
        </div>
        <h2 class="text-base font-semibold text-foreground">
          {{ t("proxies.monitoring.networkSection") }}
        </h2>
        <span class="text-xs text-foreground-muted"
          >({{ filteredNetworks.length }} / {{ currentNetworks.length }}
          {{ t("proxies.detail.total") }})</span
        >
      </div>
      <div class="divide-y divide-border">
        <div
          v-for="nic in filteredNetworks"
          :key="nic.name"
          class="p-4 hover:bg-hover transition-colors">
          <div class="flex items-center gap-3">
            <WifiIcon class="w-5 h-5 text-purple-500" />
            <div class="flex-1">
              <p class="text-sm font-medium text-foreground">{{ nic.name }}</p>
              <p class="mt-1 text-xs text-foreground-secondary">
                <span class="inline-flex items-center gap-1">
                  <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                  RX {{ bytes(nic.bytes_recv) }}
                </span>
                <span class="mx-2">·</span>
                <span class="inline-flex items-center gap-1">
                  <span class="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                  TX {{ bytes(nic.bytes_sent) }}
                </span>
              </p>
              <p class="mt-1 text-xs text-foreground-muted">
                {{ (nic.addresses || []).join(", ") || "-" }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
