import { computed, unref, type Ref } from "vue";

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

type MaybeRef<T> = Ref<T> | T;
type Translate = (key: string) => string;

const chartColors = {
  cpu: "#6366f1",
  memory: "#10b981",
  disk: "#f59e0b",
  mounts: "#f59e0b",
  readIops: "#3b82f6",
  writeIops: "#10b981",
  readBandwidth: "#8b5cf6",
  writeBandwidth: "#ec4899",
};

function formatTime(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString();
}

function sampleTimestamps(timestamps: string[]) {
  if (timestamps.length <= 12) return timestamps;
  const step = Math.ceil(timestamps.length / 12);
  return timestamps.filter((_, index) => index % step === 0);
}

function samplePoints<T>(points: T[]) {
  if (points.length <= 12) return points;
  const step = Math.ceil(points.length / 12);
  return points.filter((_, index) => index % step === 0);
}

function lineSeries(name: string, data: number[], color: string) {
  return {
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
  };
}

function baseLineChartOption(options: {
  labels: string[];
  legend?: string[];
  yFormatter: string;
  max?: number;
  series: ReturnType<typeof lineSeries>[];
}) {
  return {
    tooltip: { trigger: "axis", axisPointer: { type: "cross" } },
    ...(options.legend
      ? {
          legend: { data: options.legend, top: 0, textStyle: { fontSize: 10 } },
        }
      : {}),
    grid: {
      left: "3%",
      right: "4%",
      bottom: "3%",
      containLabel: true,
      top: options.legend ? "15%" : "8%",
    },
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
      ...(options.max ? { max: options.max } : {}),
      splitLine: { lineStyle: { type: "dashed", color: "#e2e8f0" } },
      axisLabel: {
        formatter: options.yFormatter,
        color: "#64748b",
        fontSize: 10,
      },
    },
    series: options.series,
  };
}

export function useGatewayMonitorCharts(
  monitoringData: MaybeRef<HeartbeatData[]>,
  diskIo: MaybeRef<DiskIoPoint[]>,
  selectedDisk: Ref<string>,
  t: Translate,
) {
  const sampledHeartbeats = computed(() => samplePoints(unref(monitoringData)));
  const heartbeatLabels = computed(() =>
    sampledHeartbeats.value.map((item) => formatTime(item.timestamp)),
  );

  const uniqueDisks = computed(() => {
    const disks = new Set<string>();
    unref(diskIo).forEach((item) => {
      if (item.disk) disks.add(item.disk);
    });
    return Array.from(disks);
  });

  const filteredDiskIo = computed(() => {
    const points = unref(diskIo);
    if (!selectedDisk.value) return points;
    return points.filter((item) => item.disk === selectedDisk.value);
  });

  const hasDiskIo = computed(() => filteredDiskIo.value.length > 0);

  function singleMetricChartOption(
    name: string,
    key: "cpu_usage" | "memory_usage" | "disk_usage" | "active_mounts",
    color: string,
    yFormatter: string,
    max?: number,
  ) {
    return baseLineChartOption({
      labels: heartbeatLabels.value,
      yFormatter,
      max,
      series: [
        lineSeries(
          name,
          sampledHeartbeats.value.map((item) => item[key] || 0),
          color,
        ),
      ],
    });
  }

  function groupedDiskIoData(
    readKey: "r_s" | "rkB_s",
    writeKey: "w_s" | "wkB_s",
  ) {
    const readGrouped = new Map<string, number>();
    const writeGrouped = new Map<string, number>();

    filteredDiskIo.value.forEach((item) => {
      const ts = item.timestamp;
      readGrouped.set(ts, (readGrouped.get(ts) || 0) + (item[readKey] || 0));
      writeGrouped.set(ts, (writeGrouped.get(ts) || 0) + (item[writeKey] || 0));
    });

    const timestamps = sampleTimestamps(
      Array.from(
        new Set([...readGrouped.keys(), ...writeGrouped.keys()]),
      ).sort(),
    );

    return {
      labels: timestamps.map(formatTime),
      readData: timestamps.map((ts) => readGrouped.get(ts) || 0),
      writeData: timestamps.map((ts) => writeGrouped.get(ts) || 0),
    };
  }

  const cpuChartOption = computed(() =>
    singleMetricChartOption(
      t("gateways.monitoring.cpu"),
      "cpu_usage",
      chartColors.cpu,
      "{value}%",
      100,
    ),
  );

  const memoryChartOption = computed(() =>
    singleMetricChartOption(
      t("gateways.monitoring.memory"),
      "memory_usage",
      chartColors.memory,
      "{value}%",
      100,
    ),
  );

  const diskChartOption = computed(() =>
    singleMetricChartOption(
      t("gateways.monitoring.disk"),
      "disk_usage",
      chartColors.disk,
      "{value}%",
      100,
    ),
  );

  const mountChartOption = computed(() =>
    singleMetricChartOption(
      t("gateways.activeMounts"),
      "active_mounts",
      chartColors.mounts,
      "{value}",
    ),
  );

  const diskIopsChartOption = computed(() => {
    const chartData = groupedDiskIoData("r_s", "w_s");
    const readLabel = t("gateways.monitoring.readIops");
    const writeLabel = t("gateways.monitoring.writeIops");
    return baseLineChartOption({
      labels: chartData.labels,
      legend: [readLabel, writeLabel],
      yFormatter: "{value}/s",
      series: [
        lineSeries(readLabel, chartData.readData, chartColors.readIops),
        lineSeries(writeLabel, chartData.writeData, chartColors.writeIops),
      ],
    });
  });

  const diskBandwidthChartOption = computed(() => {
    const chartData = groupedDiskIoData("rkB_s", "wkB_s");
    const readLabel = t("gateways.monitoring.readBandwidth");
    const writeLabel = t("gateways.monitoring.writeBandwidth");
    return baseLineChartOption({
      labels: chartData.labels,
      legend: [readLabel, writeLabel],
      yFormatter: "{value} kB/s",
      series: [
        lineSeries(readLabel, chartData.readData, chartColors.readBandwidth),
        lineSeries(writeLabel, chartData.writeData, chartColors.writeBandwidth),
      ],
    });
  });

  return {
    uniqueDisks,
    hasDiskIo,
    cpuChartOption,
    memoryChartOption,
    diskChartOption,
    diskIopsChartOption,
    diskBandwidthChartOption,
    mountChartOption,
  };
}
