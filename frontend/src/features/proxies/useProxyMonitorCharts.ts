import { computed, unref, type Ref } from "vue";

type MonitorDataRef = Ref<any> | (() => any);

const chartColors = {
  cpu: "#6366f1",
  memory: "#10b981",
  disk: "#f59e0b",
};

function resolveMonitorData(monitorData: MonitorDataRef) {
  return typeof monitorData === "function" ? monitorData() : unref(monitorData);
}

function formatTime(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString();
}

function sampleTimestamps(timestamps: string[]) {
  if (timestamps.length <= 12) return timestamps;
  const step = Math.ceil(timestamps.length / 12);
  return timestamps.filter((_, index) => index % step === 0);
}

export function useProxyMonitorCharts(
  monitorData: MonitorDataRef,
  selectedNetIOInterface: Ref<string>,
  selectedDiskIO: Ref<string>,
) {
  const networkIOStats = computed(() => {
    const data = resolveMonitorData(monitorData)?.network_io || [];
    return {
      rxPackets: data.reduce(
        (sum: number, item: { rx_packets?: number }) =>
          sum + (item.rx_packets || 0),
        0,
      ),
      txPackets: data.reduce(
        (sum: number, item: { tx_packets?: number }) =>
          sum + (item.tx_packets || 0),
        0,
      ),
      rxDrop: data.reduce(
        (sum: number, item: { rx_drop?: number }) => sum + (item.rx_drop || 0),
        0,
      ),
      txErrs: data.reduce(
        (sum: number, item: { tx_errs?: number }) => sum + (item.tx_errs || 0),
        0,
      ),
    };
  });

  function getChartData(type: "cpu" | "memory" | "disk") {
    const data = resolveMonitorData(monitorData);
    if (!data) {
      return { labels: [], data: [], label: "", color: "" };
    }

    let points: { timestamp: string; value: number }[] = [];
    let label = "";
    const color = chartColors[type];

    if (type === "cpu") {
      points = data.cpu_usage || [];
      label = "CPU";
    } else if (type === "memory") {
      points = data.memory_usage || [];
      label = "Memory";
    } else {
      points = data.disk_usage || [];
      label = "Disk";
    }

    if (points.length > 12) {
      const step = Math.ceil(points.length / 12);
      points = points.filter((_, index) => index % step === 0);
    }

    return {
      labels: points.map((point) =>
        new Date(point.timestamp).toLocaleTimeString(),
      ),
      data: points.map((point) => point.value),
      label,
      color,
    };
  }

  function getUniqueNetworkInterfaces(): string[] {
    const data = resolveMonitorData(monitorData);
    if (!data?.network_io) return [];
    const interfaces = new Set<string>();
    data.network_io.forEach((item: { interface?: string }) => {
      if (item.interface) interfaces.add(item.interface);
    });
    return Array.from(interfaces);
  }

  function getUniqueDisks(): string[] {
    const data = resolveMonitorData(monitorData);
    if (!data?.disk_io) return [];
    const disks = new Set<string>();
    data.disk_io.forEach((item: { disk?: string }) => {
      if (item.disk) disks.add(item.disk);
    });
    return Array.from(disks);
  }

  function getLineChartOption(type: "cpu" | "memory" | "disk") {
    const chartData = getChartData(type);
    return {
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "cross" },
      },
      grid: {
        left: "3%",
        right: "4%",
        bottom: "3%",
        containLabel: true,
      },
      xAxis: {
        type: "category",
        boundaryGap: false,
        data: chartData.labels,
        axisLine: { lineStyle: { color: "#94a3b8" } },
        axisLabel: { color: "#94a3b8", fontSize: 10 },
      },
      yAxis: {
        type: "value",
        min: 0,
        max: 100,
        splitLine: { lineStyle: { type: "dashed", color: "#e2e8f0" } },
        axisLabel: { formatter: "{value}%", color: "#64748b", fontSize: 10 },
      },
      series: [
        {
          name: chartData.label,
          type: "line",
          data: chartData.data,
          smooth: true,
          lineStyle: { color: chartData.color },
          areaStyle: {
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: chartData.color },
                { offset: 1, color: chartData.color + "05" },
              ],
            },
          },
          symbolSize: 4,
          showSymbol: false,
        },
      ],
    };
  }

  function getCPUChartOption() {
    return getLineChartOption("cpu");
  }

  function getMemoryChartOption() {
    return getLineChartOption("memory");
  }

  function getDiskChartOption() {
    return getLineChartOption("disk");
  }

  function getNetworkBytesChartData() {
    const data = resolveMonitorData(monitorData);
    if (!data?.network_io) return { labels: [], rxData: [], txData: [] };

    let filtered = data.network_io;
    if (selectedNetIOInterface.value) {
      filtered = filtered.filter(
        (item: { interface?: string }) =>
          item.interface === selectedNetIOInterface.value,
      );
    }

    const rxGrouped = new Map<string, number>();
    const txGrouped = new Map<string, number>();

    filtered.forEach(
      (item: { timestamp: string; rx_bytes?: number; tx_bytes?: number }) => {
        const ts = item.timestamp;
        if (item.rx_bytes !== undefined) {
          rxGrouped.set(ts, (rxGrouped.get(ts) || 0) + item.rx_bytes);
        }
        if (item.tx_bytes !== undefined) {
          txGrouped.set(ts, (txGrouped.get(ts) || 0) + item.tx_bytes);
        }
      },
    );

    const sorted = sampleTimestamps(
      Array.from(new Set([...rxGrouped.keys(), ...txGrouped.keys()])).sort(),
    );

    return {
      labels: sorted.map((ts) => formatTime(ts)),
      rxData: sorted.map((ts) => (rxGrouped.get(ts) || 0) / (1024 * 1024)),
      txData: sorted.map((ts) => (txGrouped.get(ts) || 0) / (1024 * 1024)),
    };
  }

  function getNetworkPacketsChartData() {
    const data = resolveMonitorData(monitorData);
    if (!data?.network_io) return { labels: [], rxData: [], txData: [] };

    let filtered = data.network_io;
    if (selectedNetIOInterface.value) {
      filtered = filtered.filter(
        (item: { interface?: string }) =>
          item.interface === selectedNetIOInterface.value,
      );
    }

    const rxGrouped = new Map<string, number>();
    const txGrouped = new Map<string, number>();

    filtered.forEach(
      (item: {
        timestamp: string;
        rx_packets?: number;
        tx_packets?: number;
      }) => {
        const ts = item.timestamp;
        if (item.rx_packets !== undefined) {
          rxGrouped.set(ts, (rxGrouped.get(ts) || 0) + item.rx_packets);
        }
        if (item.tx_packets !== undefined) {
          txGrouped.set(ts, (txGrouped.get(ts) || 0) + item.tx_packets);
        }
      },
    );

    const sorted = sampleTimestamps(
      Array.from(new Set([...rxGrouped.keys(), ...txGrouped.keys()])).sort(),
    );

    return {
      labels: sorted.map((ts) => formatTime(ts)),
      rxData: sorted.map((ts) => rxGrouped.get(ts) || 0),
      txData: sorted.map((ts) => txGrouped.get(ts) || 0),
    };
  }

  function getDiskIOPSChartData() {
    const data = resolveMonitorData(monitorData);
    if (!data?.disk_io) return { labels: [], readData: [], writeData: [] };

    let filtered = data.disk_io;
    if (selectedDiskIO.value) {
      filtered = filtered.filter(
        (item: { disk?: string }) => item.disk === selectedDiskIO.value,
      );
    }

    const rGrouped = new Map<string, number>();
    const wGrouped = new Map<string, number>();

    filtered.forEach(
      (item: { timestamp: string; r_s?: number; w_s?: number }) => {
        const ts = item.timestamp;
        if (item.r_s !== undefined) {
          rGrouped.set(ts, (rGrouped.get(ts) || 0) + item.r_s);
        }
        if (item.w_s !== undefined) {
          wGrouped.set(ts, (wGrouped.get(ts) || 0) + item.w_s);
        }
      },
    );

    const sorted = sampleTimestamps(
      Array.from(new Set([...rGrouped.keys(), ...wGrouped.keys()])).sort(),
    );

    return {
      labels: sorted.map((ts) => formatTime(ts)),
      readData: sorted.map((ts) => rGrouped.get(ts) || 0),
      writeData: sorted.map((ts) => wGrouped.get(ts) || 0),
    };
  }

  function getDiskBandwidthChartData() {
    const data = resolveMonitorData(monitorData);
    if (!data?.disk_io) return { labels: [], readData: [], writeData: [] };

    let filtered = data.disk_io;
    if (selectedDiskIO.value) {
      filtered = filtered.filter(
        (item: { disk?: string }) => item.disk === selectedDiskIO.value,
      );
    }

    const rGrouped = new Map<string, number>();
    const wGrouped = new Map<string, number>();

    filtered.forEach(
      (item: { timestamp: string; rkB_s?: number; wkB_s?: number }) => {
        const ts = item.timestamp;
        if (item.rkB_s !== undefined) {
          rGrouped.set(ts, (rGrouped.get(ts) || 0) + item.rkB_s);
        }
        if (item.wkB_s !== undefined) {
          wGrouped.set(ts, (wGrouped.get(ts) || 0) + item.wkB_s);
        }
      },
    );

    const sorted = sampleTimestamps(
      Array.from(new Set([...rGrouped.keys(), ...wGrouped.keys()])).sort(),
    );

    return {
      labels: sorted.map((ts) => formatTime(ts)),
      readData: sorted.map((ts) => rGrouped.get(ts) || 0),
      writeData: sorted.map((ts) => wGrouped.get(ts) || 0),
    };
  }

  function getDiskUtilAwaitChartData() {
    const data = resolveMonitorData(monitorData);
    if (!data?.disk_io) return { labels: [], utilData: [], awaitData: [] };

    let filtered = data.disk_io;
    if (selectedDiskIO.value) {
      filtered = filtered.filter(
        (item: { disk?: string }) => item.disk === selectedDiskIO.value,
      );
    }

    const utilGrouped = new Map<string, number>();
    const awaitGrouped = new Map<string, number>();

    filtered.forEach(
      (item: { timestamp: string; utilization?: number; await?: number }) => {
        const ts = item.timestamp;
        if (item.utilization !== undefined) {
          utilGrouped.set(ts, (utilGrouped.get(ts) || 0) + item.utilization);
        }
        if (item.await !== undefined) {
          awaitGrouped.set(ts, (awaitGrouped.get(ts) || 0) + item.await);
        }
      },
    );

    const sorted = sampleTimestamps(
      Array.from(
        new Set([...utilGrouped.keys(), ...awaitGrouped.keys()]),
      ).sort(),
    );

    return {
      labels: sorted.map((ts) => formatTime(ts)),
      utilData: sorted.map((ts) => utilGrouped.get(ts) || 0),
      awaitData: sorted.map((ts) => awaitGrouped.get(ts) || 0),
    };
  }

  function getNetworkBytesChartOption() {
    const chartData = getNetworkBytesChartData();
    return dualLineChartOption({
      labels: chartData.labels,
      legend: ["RX Bytes", "TX Bytes"],
      series: [
        ["RX Bytes", chartData.rxData, "#3b82f6"],
        ["TX Bytes", chartData.txData, "#10b981"],
      ],
      yFormatter: "{value} MB",
    });
  }

  function getNetworkPacketsChartOption() {
    const chartData = getNetworkPacketsChartData();
    return dualLineChartOption({
      labels: chartData.labels,
      legend: ["RX Packets", "TX Packets"],
      series: [
        ["RX Packets", chartData.rxData, "#8b5cf6"],
        ["TX Packets", chartData.txData, "#f59e0b"],
      ],
      yFormatter: "{value}",
    });
  }

  function getDiskIOPSChartOption() {
    const chartData = getDiskIOPSChartData();
    return dualLineChartOption({
      labels: chartData.labels,
      legend: ["Read IOPS", "Write IOPS"],
      series: [
        ["Read IOPS", chartData.readData, "#3b82f6"],
        ["Write IOPS", chartData.writeData, "#10b981"],
      ],
      yFormatter: "{value}/s",
    });
  }

  function getDiskBandwidthChartOption() {
    const chartData = getDiskBandwidthChartData();
    return dualLineChartOption({
      labels: chartData.labels,
      legend: ["Read BW", "Write BW"],
      series: [
        ["Read BW", chartData.readData, "#8b5cf6"],
        ["Write BW", chartData.writeData, "#ec4899"],
      ],
      yFormatter: "{value} kB/s",
    });
  }

  function getDiskUtilAwaitChartOption() {
    const chartData = getDiskUtilAwaitChartData();
    return {
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "cross" },
      },
      legend: {
        data: ["Utilization (%)", "Await (ms)"],
        top: 0,
        textStyle: { fontSize: 10 },
      },
      grid: {
        left: "3%",
        right: "4%",
        bottom: "3%",
        containLabel: true,
        top: "15%",
      },
      xAxis: {
        type: "category",
        boundaryGap: false,
        data: chartData.labels,
        axisLine: { lineStyle: { color: "#94a3b8" } },
        axisLabel: { color: "#94a3b8", fontSize: 10 },
      },
      yAxis: [
        {
          type: "value",
          name: "Utilization",
          min: 0,
          max: 100,
          splitLine: { lineStyle: { type: "dashed", color: "#e2e8f0" } },
          axisLabel: { formatter: "{value}%", color: "#64748b", fontSize: 10 },
          nameTextStyle: { fontSize: 10 },
        },
        {
          type: "value",
          name: "Await",
          min: 0,
          splitLine: { show: false },
          axisLabel: { formatter: "{value}ms", color: "#64748b", fontSize: 10 },
          nameTextStyle: { fontSize: 10 },
        },
      ],
      series: [
        {
          name: "Utilization (%)",
          type: "line",
          yAxisIndex: 0,
          data: chartData.utilData,
          smooth: true,
          lineStyle: { color: "#ef4444" },
          symbolSize: 4,
          showSymbol: false,
        },
        {
          name: "Await (ms)",
          type: "line",
          yAxisIndex: 1,
          data: chartData.awaitData,
          smooth: true,
          lineStyle: { color: "#f59e0b" },
          symbolSize: 4,
          showSymbol: false,
        },
      ],
    };
  }

  return {
    networkIOStats,
    getUniqueNetworkInterfaces,
    getUniqueDisks,
    getCPUChartOption,
    getMemoryChartOption,
    getDiskChartOption,
    getDiskUtilAwaitChartOption,
    getDiskIOPSChartOption,
    getDiskBandwidthChartOption,
    getNetworkBytesChartOption,
    getNetworkPacketsChartOption,
  };
}

function dualLineChartOption(options: {
  labels: string[];
  legend: string[];
  series: [string, number[], string][];
  yFormatter: string;
}) {
  return {
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "cross" },
    },
    legend: {
      data: options.legend,
      top: 0,
      textStyle: { fontSize: 10 },
    },
    grid: {
      left: "3%",
      right: "4%",
      bottom: "3%",
      containLabel: true,
      top: "15%",
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
      splitLine: { lineStyle: { type: "dashed", color: "#e2e8f0" } },
      axisLabel: {
        formatter: options.yFormatter,
        color: "#64748b",
        fontSize: 10,
      },
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
            { offset: 1, color: color + "05" },
          ],
        },
      },
      symbolSize: 4,
      showSymbol: false,
    })),
  };
}
