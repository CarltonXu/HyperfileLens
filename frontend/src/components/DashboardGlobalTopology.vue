<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import {
  Handle,
  MarkerType,
  Position,
  VueFlow,
  useVueFlow,
  type Edge,
  type Node,
} from "@vue-flow/core";
import { Background } from "@vue-flow/background";
import {
  ArrowDownTrayIcon,
  ArrowsPointingOutIcon,
  ChartBarIcon,
  CircleStackIcon,
  CloudIcon,
  ComputerDesktopIcon,
  CpuChipIcon,
  CubeIcon,
  FolderIcon,
  GlobeAltIcon,
  HomeIcon,
  MinusIcon,
  PlusIcon,
  QueueListIcon,
  ServerIcon,
  ServerStackIcon,
  ShieldCheckIcon,
  SparklesIcon,
  WindowIcon,
  BellIcon,
  BoltIcon,
  CogIcon,
  UsersIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline";
import "@vue-flow/core/dist/style.css";
import "@vue-flow/core/dist/theme-default.css";

interface TopologyNodeData {
  kind: "group" | "service" | "storage" | "compact" | "infra-services";
  title: string;
  subtitle?: string;
  icon?: any;
  tone?: "entry" | "control" | "runtime" | "storage" | "insight" | "infra";
  width?: number;
  height?: number;
  handles?: {
    left?: boolean;
    right?: boolean;
    top?: boolean;
    bottom?: boolean;
  };
  chips?: string[];
  items?: Array<{
    label: string;
    detail?: string;
    description?: string;
    service?: string;
    icon: any;
  }>;
}

const { locale } = useI18n();
const isExpanded = ref(false);
const topologyExportRef = ref<HTMLElement | null>(null);
const expandedFlowId = "dashboard-global-topology-expanded";
const { zoomTo, fitView, viewport } = useVueFlow(expandedFlowId);
const currentZoom = ref(1);

// Watch viewport changes to sync zoom display
watch(viewport, (v) => {
  currentZoom.value = v.zoom;
}, { immediate: true, deep: true });

// Watch for expanded state to get VueFlow instance after it's mounted
watch(isExpanded, (expanded) => {
  if (expanded) {
    nextTick(() => {
      setTimeout(() => {
        fitView({ padding: 0.1, duration: 300 });
        currentZoom.value = 1;
      }, 100);
    });
  }
});

const zoomIn = () => {
  const newZoom = Math.min(2, currentZoom.value + 0.1);
  zoomTo(newZoom, { duration: 200 });
  currentZoom.value = newZoom;
};

const zoomOut = () => {
  const newZoom = Math.max(0.3, currentZoom.value - 0.1);
  zoomTo(newZoom, { duration: 200 });
  currentZoom.value = newZoom;
};

const resetView = () => {
  fitView({ padding: 0.1, duration: 300 });
  currentZoom.value = 1;
};

const copy = computed(() => {
  const zh = locale.value === "zh-CN";
  return {
    title: zh ? "全局架构拓扑" : "Global Architecture Topology",
    subtitle: zh
      ? "从用户入口、控制面、Proxy 执行节点、Kopia 仓库到 Gateway 洞察节点，展示产品运行链路和核心技术流。"
      : "Shows how users, the control plane, proxy executors, Kopia repositories, and gateway insight nodes work together.",
    entryZone: zh ? "用户与数据入口" : "Users and Sources",
    controlZone: zh ? "控制面" : "Control Plane",
    runtimeZone: zh ? "执行面" : "Execution Plane",
    storageZone: zh ? "仓库与存储" : "Repository and Storage",
    insightZone: zh ? "洞察分析" : "Insight Analysis",
    infraZone: zh ? "平台基础服务" : "Platform Services",
    browser: zh ? "Web 控制台" : "Web Console",
    browserDesc: zh
      ? "租户、策略、任务、恢复与审计管理"
      : "Tenant, policy, task, recovery, and audit management",
    source: zh ? "源端数据" : "Source Data",
    sourceDesc: "Local FS / NAS / NFS / SMB",
    sourceItems: [
      {
        label: "Local FS",
        detail: zh ? "本地文件系统" : "local filesystem",
        icon: FolderIcon,
      },
      {
        label: "NAS/NFS/CIFS",
        detail: zh ? "网络共享目录" : "network shares",
        icon: CircleStackIcon,
      },
    ],
    api: zh ? "Django ASGI API" : "Django ASGI API",
    apiDesc: zh
      ? "REST API / WebSocket / 权限与审计"
      : "REST API / WebSocket / auth and audit",
    scheduler: zh ? "任务编排" : "Task Orchestration",
    schedulerDesc: zh
      ? "策略调度、队列分发、状态聚合"
      : "Policy scheduling, queue dispatch, status aggregation",
    proxy: zh ? "Proxy 节点" : "Proxy Nodes",
    proxyDesc: zh
      ? "Go Agent，执行备份、恢复、挂载、维护"
      : "Go agent for backup, restore, mount, and maintenance",
    proxyItems: [
      {
        label: "Agent Proxy",
        detail: zh ? "多节点" : "multi-node",
        description: zh
          ? "源端生产系统安装 Agent，备份本地的文件系统目录"
          : "Installed on source production systems to back up local filesystem paths",
        service: "Kopia CLI",
        icon: ComputerDesktopIcon,
      },
      {
        label: "Sync Proxy",
        detail: zh ? "多节点" : "multi-node",
        description: zh
          ? "独立代理节点，可代理本地文件系统目录、NAS/NFS/CIFS 进行备份"
          : "Standalone proxy node for local filesystem, NAS, NFS, and CIFS backups",
        service: "Kopia CLI",
        icon: ServerStackIcon,
      },
    ],
    repository: zh ? "Kopia Repository" : "Kopia Repository",
    repositoryDesc: zh
      ? "快照、去重块、策略保留点"
      : "Snapshots, deduplicated blobs, retention points",
    gateway: zh ? "Gateway 节点" : "Gateway Nodes",
    gatewayDesc: zh
      ? "Ubuntu Agent，挂载快照并本地索引"
      : "Ubuntu agent mounts snapshots and builds local indexes",
    insights: zh ? "AI Insights" : "AI Insights",
    insightsDesc: zh
      ? "搜索、冷热、重复、敏感数据分析"
      : "Search, heat, duplicate, and sensitive data analysis",
    infra: "PostgreSQL / Redis / Celery / Alerting",
    infraDesc: zh
      ? "业务元数据、任务队列、心跳指标、告警通知"
      : "Metadata, task queues, heartbeats, metrics, and notifications",
    restFlow: "HTTPS REST",
    wsFlow: "WSS Control",
    queueFlow: zh ? "任务下发" : "Task dispatch",
    dataFlow: zh ? "Kopia 备份/恢复数据流" : "Kopia backup / restore data",
    sourceDataFlow: zh ? "源数据读取" : "Source read",
    repoDataFlow: zh ? "备份/恢复" : "Backup / restore",
    storageFlow: zh ? "存储后端连接" : "Storage backend",
    insightFlow: zh ? "快照读取/索引" : "Snapshot read / index",
    snapshotFlow: zh ? "快照读取" : "Snapshot read",
    metaFlow: zh ? "元数据/心跳/告警" : "Metadata / heartbeat / alerts",
    repoItems: [
      {
        label: zh ? "本地文件系统" : "Local Filesystem",
        detail: "filesystem",
        icon: FolderIcon,
      },
      {
        label: "NAS / NFS / SMB",
        detail: "mounted path",
        icon: CircleStackIcon,
      },
      {
        label: zh ? "S3 对象存储" : "S3 Object Storage",
        detail: "s3 compatible",
        icon: CloudIcon,
      },
    ],
    infraItems: [
      {
        label: "PostgreSQL",
        detail: zh ? "业务元数据" : "Metadata",
        icon: CubeIcon,
      },
      {
        label: "Redis",
        detail: zh ? "任务队列与缓存" : "Queue & Cache",
        icon: CogIcon,
      },
      {
        label: "Celery",
        detail: zh ? "异步任务执行" : "Async Tasks",
        icon: BoltIcon,
      },
      {
        label: "Alerting",
        detail: zh ? "告警通知" : "Notifications",
        icon: BellIcon,
      },
    ],
    expand: zh ? "放大全局查看" : "Expand topology",
    downloadSnapshot: zh ? "下载 SVG" : "Download SVG",
    close: zh ? "关闭" : "Close",
    autoLayout: zh ? "自动布局" : "Auto Layout",
    zoomIn: zh ? "放大" : "Zoom In",
    zoomOut: zh ? "缩小" : "Zoom Out",
    resetView: zh ? "重置视图" : "Reset View",
  };
});

const downloadBlobFile = (filename: string, blob: Blob) => {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
};

const inlineComputedStyles = (source: Element, target: Element) => {
  const computed = window.getComputedStyle(source);
  let style = "";
  for (const property of computed) {
    style += `${property}:${computed.getPropertyValue(property)};`;
  }
  target.setAttribute("style", style);

  Array.from(source.children).forEach((sourceChild, index) => {
    const targetChild = target.children[index];
    if (targetChild) {
      inlineComputedStyles(sourceChild, targetChild);
    }
  });
};

const downloadTopologySnapshot = async () => {
  await nextTick();
  await fitView({
    padding: 0.08,
    duration: 0,
  });
  await nextTick();
  await new Promise((resolve) => window.setTimeout(resolve, 80));

  const source = topologyExportRef.value;
  if (!source) return;

  const rect = source.getBoundingClientRect();
  const width = Math.ceil(rect.width);
  const height = Math.ceil(rect.height);
  const clone = source.cloneNode(true) as HTMLElement;
  clone.setAttribute("xmlns", "http://www.w3.org/1999/xhtml");
  clone.style.width = `${width}px`;
  clone.style.height = `${height}px`;
  inlineComputedStyles(source, clone);

  const serialized = new XMLSerializer().serializeToString(clone);
  const svg = `<?xml version="1.0" encoding="UTF-8"?>
    <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
      <foreignObject width="100%" height="100%">${serialized}</foreignObject>
    </svg>`;
  downloadBlobFile(
    "hyperfilelens-architecture-topology.svg",
    new Blob([svg], { type: "image/svg+xml;charset=utf-8" }),
  );
};

const edgeColors = {
  rest: "#0284c7",
  control: "#7c3aed",
  data: "#059669",
  storage: "#d97706",
  insight: "#db2777",
  meta: "#64748b",
};

const edgeDefaults = {
  type: "smoothstep",
  animated: true,
  labelBgPadding: [8, 4] as [number, number],
  labelBgBorderRadius: 6,
  labelStyle: {
    fill: "var(--foreground)",
    fontSize: 11,
    fontWeight: 700,
  },
  labelBgStyle: {
    fill: "var(--card)",
    fillOpacity: 0.92,
  },
};

const layout = {
  entry: { x: 28, y: 64, width: 250, height: 500 },
  control: { x: 332, y: 28, width: 350, height: 330 },
  runtime: { x: 332, y: 380, width: 350, height: 330 },
  storage: { x: 780, y: 380, width: 318, height: 330 },
  insight: { x: 1180, y: 380, width: 280, height: 330 },
  infra: { x: 332, y: 760, width: 766, height: 200 },
};

const centerX = (zone: { x: number; width: number }, nodeWidth: number) =>
  zone.x + (zone.width - nodeWidth) / 2;

const nodes = computed<Node<TopologyNodeData>[]>(() => [
  {
    id: "entry-group",
    type: "global",
    position: { x: layout.entry.x, y: layout.entry.y },
    selectable: false,
    draggable: false,
    style: { zIndex: 0 },
    data: {
      kind: "group",
      title: copy.value.entryZone,
      icon: UsersIcon,
      tone: "entry",
      width: layout.entry.width,
      height: layout.entry.height,
    },
  },
  {
    id: "control-group",
    type: "global",
    position: { x: layout.control.x, y: layout.control.y },
    selectable: false,
    draggable: false,
    style: { zIndex: 0 },
    data: {
      kind: "group",
      title: copy.value.controlZone,
      icon: CogIcon,
      tone: "control",
      width: layout.control.width,
      height: layout.control.height,
    },
  },
  {
    id: "runtime-group",
    type: "global",
    position: { x: layout.runtime.x, y: layout.runtime.y },
    selectable: false,
    draggable: false,
    style: { zIndex: 0 },
    data: {
      kind: "group",
      title: copy.value.runtimeZone,
      icon: ServerStackIcon,
      tone: "runtime",
      width: layout.runtime.width,
      height: layout.runtime.height,
    },
  },
  {
    id: "storage-group",
    type: "global",
    position: { x: layout.storage.x, y: layout.storage.y },
    selectable: false,
    draggable: false,
    style: { zIndex: 0 },
    data: {
      kind: "group",
      title: copy.value.storageZone,
      icon: CircleStackIcon,
      tone: "storage",
      width: layout.storage.width,
      height: layout.storage.height,
    },
  },
  {
    id: "insight-group",
    type: "global",
    position: { x: layout.insight.x, y: layout.insight.y },
    selectable: false,
    draggable: false,
    style: { zIndex: 0 },
    data: {
      kind: "group",
      title: copy.value.insightZone,
      icon: SparklesIcon,
      tone: "insight",
      width: layout.insight.width,
      height: layout.insight.height,
    },
  },
  {
    id: "infra-group",
    type: "global",
    position: { x: layout.infra.x, y: layout.infra.y },
    selectable: false,
    draggable: false,
    style: { zIndex: 0 },
    data: {
      kind: "group",
      title: copy.value.infraZone,
      icon: CubeIcon,
      tone: "infra",
      width: layout.infra.width,
      height: layout.infra.height,
    },
  },
  {
    id: "browser",
    type: "global",
    position: { x: centerX(layout.entry, 190), y: 132 },
    selectable: false,
    data: {
      kind: "service",
      title: copy.value.browser,
      subtitle: copy.value.browserDesc,
      icon: WindowIcon,
      tone: "entry",
      width: 190,
      handles: { right: true },
      chips: ["Vue 3", "Vite"],
    },
  },
  {
    id: "source",
    type: "global",
    position: { x: centerX(layout.entry, 210), y: 338 },
    selectable: false,
    data: {
      kind: "service",
      title: copy.value.source,
      subtitle: copy.value.sourceDesc,
      icon: FolderIcon,
      tone: "entry",
      width: 210,
      handles: { right: true },
      items: copy.value.sourceItems,
    },
  },
  {
    id: "api",
    type: "global",
    position: { x: centerX(layout.control, 242), y: 78 },
    selectable: false,
    data: {
      kind: "service",
      title: copy.value.api,
      subtitle: copy.value.apiDesc,
      icon: GlobeAltIcon,
      tone: "control",
      width: 242,
      handles: { left: true, bottom: true },
      chips: ["DRF", "Channels", "ASGI"],
    },
  },
  {
    id: "scheduler",
    type: "global",
    position: { x: centerX(layout.control, 242), y: 250 },
    selectable: false,
    data: {
      kind: "compact",
      title: copy.value.scheduler,
      subtitle: copy.value.schedulerDesc,
      icon: QueueListIcon,
      tone: "control",
      width: 242,
      handles: { top: true, right: true, bottom: true },
    },
  },
  {
    id: "proxy",
    type: "global",
    position: { x: centerX(layout.runtime, 310), y: 420 },
    selectable: false,
    data: {
      kind: "service",
      title: copy.value.proxy,
      subtitle: copy.value.proxyDesc,
      icon: ServerIcon,
      tone: "runtime",
      width: 310,
      handles: { left: true, right: true, top: true, bottom: true },
      items: copy.value.proxyItems,
    },
  },
  {
    id: "repository",
    type: "global",
    position: { x: centerX(layout.storage, 232), y: 440 },
    selectable: false,
    data: {
      kind: "storage",
      title: copy.value.repository,
      subtitle: copy.value.repositoryDesc,
      icon: ShieldCheckIcon,
      tone: "storage",
      width: 232,
      handles: { left: true, right: true, bottom: true },
      items: copy.value.repoItems,
    },
  },
  {
    id: "gateway",
    type: "global",
    position: { x: centerX(layout.insight, 208), y: 430 },
    selectable: false,
    data: {
      kind: "service",
      title: copy.value.gateway,
      subtitle: copy.value.gatewayDesc,
      icon: CpuChipIcon,
      tone: "insight",
      width: 208,
      handles: { left: true, top: true, bottom: true },
      chips: ["Kopia mount", "Indexer"],
    },
  },
  {
    id: "insights",
    type: "global",
    position: { x: centerX(layout.insight, 208), y: 590 },
    selectable: false,
    data: {
      kind: "compact",
      title: copy.value.insights,
      subtitle: copy.value.insightsDesc,
      icon: SparklesIcon,
      tone: "insight",
      width: 208,
      handles: { top: true },
    },
  },
  {
    id: "infra",
    type: "global",
    position: { x: centerX(layout.infra, 700), y: 800 },
    selectable: false,
    data: {
      kind: "infra-services",
      title: copy.value.infra,
      subtitle: copy.value.infraDesc,
      icon: CircleStackIcon,
      tone: "infra",
      width: 700,
      handles: { top: true },
      items: copy.value.infraItems,
    },
  },
]);

const edges = computed<Edge[]>(() => [
  {
    ...edgeDefaults,
    id: "browser-api",
    source: "browser",
    target: "api",
    sourceHandle: "right",
    targetHandle: "left",
    label: copy.value.restFlow,
    markerEnd: { type: MarkerType.ArrowClosed, color: edgeColors.rest },
    style: { stroke: edgeColors.rest, strokeWidth: 2.4 },
  },
  {
    ...edgeDefaults,
    id: "api-scheduler",
    source: "api",
    target: "scheduler",
    sourceHandle: "bottom",
    targetHandle: "top",
    label: copy.value.queueFlow,
    markerEnd: { type: MarkerType.ArrowClosed, color: edgeColors.control },
    style: { stroke: edgeColors.control, strokeWidth: 2.4 },
  },
  {
    ...edgeDefaults,
    id: "scheduler-proxy",
    source: "scheduler",
    target: "proxy",
    sourceHandle: "bottom",
    targetHandle: "top",
    label: copy.value.wsFlow,
    markerEnd: { type: MarkerType.ArrowClosed, color: edgeColors.control },
    style: { stroke: edgeColors.control, strokeWidth: 2.4 },
  },
  {
    ...edgeDefaults,
    id: "scheduler-gateway",
    source: "scheduler",
    target: "gateway",
    sourceHandle: "right",
    targetHandle: "top",
    label: copy.value.wsFlow,
    markerEnd: { type: MarkerType.ArrowClosed, color: edgeColors.control },
    style: { stroke: edgeColors.control, strokeWidth: 2.4 },
  },
  {
    ...edgeDefaults,
    id: "source-proxy",
    source: "source",
    target: "proxy",
    sourceHandle: "right",
    targetHandle: "left",
    label: copy.value.sourceDataFlow,
    markerEnd: { type: MarkerType.ArrowClosed, color: edgeColors.data },
    style: { stroke: edgeColors.data, strokeWidth: 2.8 },
  },
  {
    ...edgeDefaults,
    id: "proxy-repository",
    source: "proxy",
    target: "repository",
    sourceHandle: "right",
    targetHandle: "left",
    label: copy.value.repoDataFlow,
    markerEnd: { type: MarkerType.ArrowClosed, color: edgeColors.data },
    style: { stroke: edgeColors.data, strokeWidth: 2.8 },
  },
  {
    ...edgeDefaults,
    id: "repository-gateway",
    source: "repository",
    target: "gateway",
    sourceHandle: "right",
    targetHandle: "left",
    label: copy.value.snapshotFlow,
    markerEnd: { type: MarkerType.ArrowClosed, color: edgeColors.insight },
    style: { stroke: edgeColors.insight, strokeWidth: 2.6 },
  },
  {
    ...edgeDefaults,
    id: "gateway-insights",
    source: "gateway",
    target: "insights",
    sourceHandle: "bottom",
    targetHandle: "top",
    label: "AI",
    markerEnd: { type: MarkerType.ArrowClosed, color: edgeColors.insight },
    style: { stroke: edgeColors.insight, strokeWidth: 2.4 },
  },
  {
    ...edgeDefaults,
    id: "repository-infra",
    source: "repository",
    target: "infra",
    sourceHandle: "bottom",
    targetHandle: "top",
    label: copy.value.storageFlow,
    markerEnd: { type: MarkerType.ArrowClosed, color: edgeColors.storage },
    style: { stroke: edgeColors.storage, strokeWidth: 2.2 },
  },
  {
    ...edgeDefaults,
    id: "proxy-infra",
    source: "proxy",
    target: "infra",
    sourceHandle: "bottom",
    targetHandle: "top",
    label: copy.value.metaFlow,
    markerEnd: { type: MarkerType.ArrowClosed, color: edgeColors.meta },
    style: { stroke: edgeColors.meta, strokeWidth: 2.2 },
  },
]);
</script>

<template>
  <section class="dashboard-topology dashboard-topology-compact">
    <div class="dashboard-topology-header">
      <div>
        <div class="flex items-center gap-2">
          <ChartBarIcon class="h-5 w-5 text-sky-600" />
          <h2>{{ copy.title }}</h2>
        </div>
        <p>{{ copy.subtitle }}</p>
      </div>
      <div class="dashboard-topology-legends">
        <button
          type="button"
          class="topology-expand-button"
          :title="copy.expand"
          @click="isExpanded = true">
          <ArrowsPointingOutIcon class="h-4 w-4" />
          <span>{{ copy.expand }}</span>
        </button>
      </div>
    </div>

    <Teleport to="body">
      <div
        v-if="isExpanded"
        class="topology-expanded-overlay"
        role="dialog"
        aria-modal="true">
        <section class="topology-expanded-panel">
          <header class="topology-expanded-header">
            <div>
              <h2>{{ copy.title }}</h2>
              <p>{{ copy.subtitle }}</p>
            </div>
            <div class="topology-expanded-actions">
              <button
                type="button"
                class="topology-zoom-button"
                :title="copy.autoLayout"
                @click="resetView">
                <HomeIcon class="h-4 w-4" />
                <span>{{ copy.autoLayout }}</span>
              </button>
              <div class="topology-zoom-controls">
                <button
                  type="button"
                  class="topology-zoom-btn"
                  :title="copy.zoomOut"
                  @click="zoomOut">
                  <MinusIcon class="h-4 w-4" />
                </button>
                <span class="topology-zoom-level">{{ Math.round(currentZoom * 100) }}%</span>
                <button
                  type="button"
                  class="topology-zoom-btn"
                  :title="copy.zoomIn"
                  @click="zoomIn">
                  <PlusIcon class="h-4 w-4" />
                </button>
              </div>
              <button
                type="button"
                class="topology-download-button"
                :title="copy.downloadSnapshot"
                @click="downloadTopologySnapshot">
                <ArrowDownTrayIcon class="h-4 w-4" />
                <span>{{ copy.downloadSnapshot }}</span>
              </button>
              <button
                type="button"
                class="topology-close-button"
                :title="copy.close"
                @click="isExpanded = false">
                <XMarkIcon class="h-5 w-5" />
              </button>
            </div>
          </header>

          <div ref="topologyExportRef" class="topology-expanded-canvas">
            <aside class="topology-expanded-legends" aria-label="Legend">
              <h3>Legend</h3>
              <div class="topology-expanded-legend-list">
                <span class="legend-rest"><i />{{ copy.restFlow }}</span>
                <span class="legend-control"><i />{{ copy.wsFlow }}</span>
                <span class="legend-data"><i />{{ copy.dataFlow }}</span>
                <span class="legend-insight"><i />{{ copy.insightFlow }}</span>
                <span class="legend-meta"><i />{{ copy.metaFlow }}</span>
              </div>
            </aside>

            <VueFlow
              :id="expandedFlowId"
              :key="`expanded-${locale}`"
              :nodes="nodes"
              :edges="edges"
              :nodes-draggable="false"
              :nodes-connectable="false"
              :edges-updatable="false"
              :elements-selectable="false"
              :pan-on-drag="true"
              :zoom-on-scroll="true"
              :zoom-on-pinch="true"
              :min-zoom="0.3"
              :max-zoom="2"
              fit-view-on-init
              class="dashboard-topology-flow">
              <Background
                :gap="20"
                :size="1"
                pattern-color="var(--topology-grid)" />

              <template #node-global="{ data }">
                <div
                  v-if="data.kind === 'group'"
                  :class="['topology-group-node', data.tone]"
                  :style="{
                    width: `${data.width}px`,
                    height: `${data.height}px`,
                  }">
                  <span>
                    <component :is="data.icon" class="h-4 w-4" />
                    {{ data.title }}
                  </span>
                </div>

                <article
                  v-else
                  :class="['topology-card-node', data.kind, data.tone]"
                  :style="{ width: `${data.width}px` }">
                  <Handle
                    v-if="data.handles?.left"
                    id="left"
                    type="target"
                    :position="Position.Left"
                    class="topology-handle" />
                  <Handle
                    v-if="data.handles?.right"
                    id="right"
                    type="source"
                    :position="Position.Right"
                    class="topology-handle" />
                  <Handle
                    v-if="data.handles?.top"
                    id="top"
                    type="target"
                    :position="Position.Top"
                    class="topology-handle" />
                  <Handle
                    v-if="data.handles?.bottom"
                    id="bottom"
                    type="source"
                    :position="Position.Bottom"
                    class="topology-handle" />

                  <div class="topology-card-main">
                    <div class="topology-card-icon">
                      <component :is="data.icon" class="h-5 w-5" />
                    </div>
                    <div class="topology-card-copy">
                      <h3>{{ data.title }}</h3>
                      <p v-if="data.subtitle">{{ data.subtitle }}</p>
                    </div>
                  </div>

                  <div v-if="data.chips?.length" class="topology-chips">
                    <span v-for="chip in data.chips" :key="chip">
                      {{ chip }}
                    </span>
                  </div>

                  <div
                    v-if="data.items?.length && data.kind === 'infra-services'"
                    class="infra-items">
                    <div
                      v-for="item in data.items"
                      :key="item.label"
                      class="infra-item">
                      <div class="infra-item-icon">
                        <component :is="item.icon" class="h-5 w-5" />
                      </div>
                      <div class="infra-item-text">
                        <span>{{ item.label }}</span>
                        <small v-if="item.detail">{{ item.detail }}</small>
                      </div>
                    </div>
                  </div>

                  <div
                    v-else-if="data.items?.length && data.tone === 'runtime'"
                    class="proxy-options">
                    <div
                      v-for="item in data.items"
                      :key="item.label"
                      :title="item.description">
                      <component :is="item.icon" class="h-5 w-5" />
                      <div class="proxy-option-copy">
                        <div class="proxy-option-head">
                          <span>{{ item.label }}</span>
                          <small v-if="item.detail">{{ item.detail }}</small>
                        </div>
                        <p v-if="item.description">{{ item.description }}</p>
                        <b v-if="item.service">{{ item.service }}</b>
                      </div>
                    </div>
                  </div>

                  <div
                    v-else-if="data.items?.length && data.tone === 'entry'"
                    class="source-options">
                    <div v-for="item in data.items" :key="item.label">
                      <component :is="item.icon" class="h-4 w-4" />
                      <span>{{ item.label }}</span>
                      <small v-if="item.detail">{{ item.detail }}</small>
                    </div>
                  </div>

                  <div v-else-if="data.items?.length" class="target-options">
                    <div v-for="item in data.items" :key="item.label">
                      <component :is="item.icon" class="h-5 w-5" />
                      <span>{{ item.label }}</span>
                      <small v-if="item.detail">{{ item.detail }}</small>
                    </div>
                  </div>
                </article>
              </template>
            </VueFlow>
          </div>
        </section>
      </div>
    </Teleport>
  </section>
</template>

<style scoped>
.dashboard-topology {
  --topology-grid: rgb(var(--border-rgb) / 0.72);
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--card);
  box-shadow: var(--shadow-sm);
}

.dashboard-topology-header {
  display: flex;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
}

.dashboard-topology:not(.dashboard-topology-compact) .dashboard-topology-header {
  align-items: flex-start;
  border-bottom: 1px solid var(--border);
}

.dashboard-topology-header h2 {
  color: var(--foreground);
  font-size: 16px;
  font-weight: 700;
}

.dashboard-topology-header p {
  max-width: 900px;
  margin-top: 4px;
  color: var(--foreground-secondary);
  font-size: 14px;
  line-height: 1.6;
}

.dashboard-topology-legends {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
  max-width: 520px;
  font-size: 12px;
}

.dashboard-topology-compact .dashboard-topology-legends {
  max-width: none;
}

.dashboard-topology-legends span {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--card);
  padding: 5px 10px;
  color: var(--foreground-secondary);
  font-weight: 650;
  white-space: nowrap;
}

.dashboard-topology-legends i {
  width: 24px;
  height: 2px;
  border-radius: 999px;
}

.topology-expand-button,
.topology-close-button,
.topology-download-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--card);
  color: var(--foreground-secondary);
  transition:
    border-color 0.16s ease,
    color 0.16s ease,
    background 0.16s ease;
}

.topology-expand-button {
  gap: 6px;
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 700;
}

.topology-expand-button:hover,
.topology-close-button:hover,
.topology-download-button:hover {
  border-color: rgb(var(--primary-rgb) / 0.45);
  background: rgb(var(--primary-rgb) / 0.08);
  color: var(--foreground);
}

.topology-download-button {
  gap: 6px;
  height: 36px;
  padding: 0 12px;
  font-size: 13px;
  font-weight: 700;
}

.topology-close-button {
  width: 36px;
  height: 36px;
  flex: 0 0 auto;
}

.topology-zoom-button,
.topology-zoom-controls {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--card);
  color: var(--foreground);
  font-size: 13px;
  font-weight: 700;
  transition: all 0.15s ease;
}

.topology-zoom-button:hover,
.topology-zoom-controls:hover {
  border-color: rgb(var(--primary-rgb) / 0.45);
  background: rgb(var(--primary-rgb) / 0.08);
  color: var(--foreground);
}

.topology-zoom-button span {
  display: inline-block;
}

.topology-zoom-controls {
  gap: 4px;
  padding: 0 8px;
}

.topology-zoom-btn {
  display: grid;
  width: 28px;
  height: 28px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 6px;
  transition: background 0.15s ease;
}

.topology-zoom-btn:hover {
  background: rgb(var(--primary-rgb) / 0.12);
}

.topology-zoom-level {
  min-width: 48px;
  text-align: center;
  font-size: 13px;
  font-weight: 700;
  color: var(--foreground);
}

.legend-rest i {
  background: #0284c7;
}

.legend-control i {
  background: #7c3aed;
}

.legend-data i {
  background: #059669;
}

.legend-insight i {
  background: #db2777;
}

.legend-meta i {
  background: #64748b;
}

.dashboard-topology-canvas-wrap {
  height: 700px;
  margin: 20px;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 12px;
  background:
    linear-gradient(
      180deg,
      rgb(var(--background-secondary-rgb) / 0.68),
      rgb(var(--background-secondary-rgb) / 0.36)
    ),
    var(--background-secondary);
}

.dashboard-topology-flow {
  width: 100%;
  height: 100%;
}

.topology-expanded-overlay {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: flex;
  background: rgb(2 6 23 / 0.58);
  padding: 24px;
}

.topology-expanded-panel {
  --topology-grid: rgb(var(--border-rgb) / 0.72);
  display: flex;
  width: 100%;
  min-width: 0;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--card);
  box-shadow: var(--shadow-lg);
}

.topology-expanded-header {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
  border-bottom: 1px solid var(--border);
  padding: 16px 18px;
}

.topology-expanded-header h2 {
  color: var(--foreground);
  font-size: 16px;
  font-weight: 760;
}

.topology-expanded-header p {
  max-width: 980px;
  margin-top: 4px;
  color: var(--foreground-secondary);
  font-size: 13px;
  line-height: 1.5;
}

.topology-expanded-actions {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 8px;
}

.topology-expanded-canvas {
  position: relative;
  min-height: 0;
  flex: 1;
  background:
    linear-gradient(
      180deg,
      rgb(var(--background-secondary-rgb) / 0.68),
      rgb(var(--background-secondary-rgb) / 0.36)
    ),
    var(--background-secondary);
}

.topology-expanded-legends {
  position: absolute;
  top: 16px;
  right: 16px;
  z-index: 5;
  width: 280px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: rgb(var(--card-rgb) / 0.94);
  padding: 14px;
  box-shadow: var(--shadow-sm);
}

.topology-expanded-legends h3 {
  margin-bottom: 12px;
  color: var(--foreground);
  font-size: 15px;
  font-weight: 800;
}

.topology-expanded-legend-list {
  display: grid;
  gap: 12px;
}

.topology-expanded-legend-list span {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--foreground-secondary);
  font-size: 14px;
  font-weight: 700;
  line-height: 1.3;
}

.topology-expanded-legend-list i {
  width: 36px;
  height: 4px;
  flex: 0 0 auto;
  border-radius: 999px;
}

:deep(.vue-flow__node-global) {
  border: none;
  background: transparent;
  box-shadow: none;
}

:deep(.vue-flow__pane) {
  cursor: grab;
}

:deep(.vue-flow__pane.dragging) {
  cursor: grabbing;
}

:deep(.vue-flow__edge-path) {
  stroke-linecap: round;
  stroke-linejoin: round;
}

:deep(.vue-flow__edge.animated path) {
  stroke-dasharray: 9 10;
  animation-duration: 1.35s;
}

.topology-group-node {
  position: relative;
  box-sizing: border-box;
  border: 1.5px dashed;
  border-radius: 14px;
  background: rgb(var(--card-rgb) / 0.26);
  pointer-events: none;
}

.topology-group-node span {
  position: absolute;
  top: 10px;
  left: 12px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--foreground-secondary);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
}

.topology-group-node span svg {
  flex: 0 0 auto;
}

.topology-group-node.entry {
  border-color: rgb(2 132 199 / 0.5);
}

.topology-group-node.entry span svg {
  color: #0284c7;
}

.topology-group-node.control {
  border-color: rgb(124 58 237 / 0.5);
}

.topology-group-node.control span svg {
  color: #7c3aed;
}

.topology-group-node.runtime {
  border-color: rgb(5 150 105 / 0.5);
}

.topology-group-node.runtime span svg {
  color: #059669;
}

.topology-group-node.storage {
  border-color: rgb(217 119 6 / 0.52);
}

.topology-group-node.storage span svg {
  color: #d97706;
}

.topology-group-node.insight {
  border-color: rgb(219 39 119 / 0.5);
}

.topology-group-node.insight span svg {
  color: #db2777;
}

.topology-group-node.infra {
  border-color: rgb(100 116 139 / 0.55);
}

.topology-group-node.infra span svg {
  color: #64748b;
}

.topology-card-node {
  position: relative;
  box-sizing: border-box;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: rgb(var(--card-rgb) / 0.97);
  padding: 12px;
  box-shadow: var(--shadow-sm);
}

.topology-card-main {
  display: flex;
  align-items: center;
  gap: 12px;
}

.topology-card-node h3 {
  color: var(--foreground);
  font-size: 14px;
  font-weight: 760;
}

.topology-card-node p {
  margin-top: 3px;
  color: var(--foreground-secondary);
  font-size: 12px;
  line-height: 1.45;
}

.topology-card-icon {
  display: grid;
  width: 40px;
  height: 40px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 10px;
}

.topology-card-node.entry .topology-card-icon,
.topology-card-node.control .topology-card-icon {
  color: #0284c7;
  background: rgb(2 132 199 / 0.11);
}

.topology-card-node.control .topology-card-icon {
  color: #7c3aed;
  background: rgb(124 58 237 / 0.12);
}

.topology-card-node.runtime .topology-card-icon {
  color: #059669;
  background: rgb(5 150 105 / 0.12);
}

.topology-card-node.storage .topology-card-icon {
  color: #d97706;
  background: rgb(217 119 6 / 0.12);
}

.topology-card-node.insight .topology-card-icon {
  color: #db2777;
  background: rgb(219 39 119 / 0.12);
}

.topology-card-node.infra .topology-card-icon {
  color: #64748b;
  background: rgb(100 116 139 / 0.12);
}

.topology-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.topology-chips span {
  border: 1px solid var(--border);
  border-radius: 999px;
  background: rgb(var(--background-secondary-rgb) / 0.68);
  padding: 3px 8px;
  color: var(--foreground-secondary);
  font-size: 11px;
  font-weight: 700;
}

.target-options {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}

.target-options div {
  display: grid;
  grid-template-columns: 20px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  border: 1px solid rgb(217 119 6 / 0.18);
  border-radius: 8px;
  background: rgb(217 119 6 / 0.06);
  padding: 8px 9px;
  color: var(--foreground);
  font-size: 12px;
  font-weight: 700;
}

.target-options svg {
  color: #d97706;
}

.target-options small {
  color: var(--foreground-secondary);
  font-size: 10px;
  font-weight: 700;
}

.source-options {
  display: grid;
  gap: 7px;
  margin-top: 12px;
}

.source-options div {
  display: grid;
  grid-template-columns: 20px minmax(0, 1fr);
  align-items: center;
  gap: 7px;
  border: 1px solid rgb(2 132 199 / 0.16);
  border-radius: 8px;
  background: rgb(2 132 199 / 0.06);
  padding: 7px 8px;
}

.source-options svg {
  grid-row: 1 / span 2;
  align-self: center;
  color: #0284c7;
}

.source-options span {
  color: var(--foreground);
  font-size: 11px;
  font-weight: 760;
  line-height: 1.2;
}

.source-options small {
  grid-column: 2;
  color: var(--foreground-secondary);
  font-size: 10px;
  font-weight: 650;
  line-height: 1.2;
}

.proxy-options {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}

.proxy-options > div {
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr);
  align-items: center;
  min-width: 0;
  gap: 8px;
  border: 1px solid rgb(5 150 105 / 0.18);
  border-radius: 8px;
  background: rgb(5 150 105 / 0.06);
  padding: 9px 10px;
}

.proxy-options svg {
  justify-self: center;
  color: #059669;
}

.proxy-option-copy {
  display: grid;
  min-width: 0;
  gap: 5px;
}

.proxy-option-head {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.proxy-option-head span {
  max-width: 100%;
  overflow: hidden;
  color: var(--foreground);
  font-size: 12px;
  font-weight: 760;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.proxy-option-head small {
  flex: 0 0 auto;
  color: var(--foreground-secondary);
  font-size: 10px;
  font-weight: 650;
  line-height: 1.2;
  white-space: nowrap;
}

.proxy-option-copy p {
  margin: 0;
  color: var(--foreground-secondary);
  font-size: 10px;
  font-weight: 600;
  line-height: 1.35;
}

.proxy-option-copy b {
  width: fit-content;
  border: 1px solid rgb(5 150 105 / 0.2);
  border-radius: 999px;
  background: rgb(5 150 105 / 0.08);
  padding: 2px 7px;
  color: #059669;
  font-size: 10px;
  font-weight: 800;
  line-height: 1.2;
}

.infra-items {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-top: 12px;
}

.infra-item {
  display: flex;
  align-items: center;
  gap: 10px;
  border-radius: 8px;
  background: rgb(var(--background-secondary-rgb) / 0.5);
  padding: 10px 12px;
}

.infra-item:nth-child(1) {
  border: 1px solid rgb(59 130 246 / 0.25);
}
.infra-item:nth-child(1) .infra-item-icon {
  background: rgb(59 130 246 / 0.14);
  color: #3b82f6;
}

.infra-item:nth-child(2) {
  border: 1px solid rgb(249 115 22 / 0.25);
}
.infra-item:nth-child(2) .infra-item-icon {
  background: rgb(249 115 22 / 0.14);
  color: #f97316;
}

.infra-item:nth-child(3) {
  border: 1px solid rgb(34 197 94 / 0.25);
}
.infra-item:nth-child(3) .infra-item-icon {
  background: rgb(34 197 94 / 0.14);
  color: #22c55e;
}

.infra-item:nth-child(4) {
  border: 1px solid rgb(234 179 8 / 0.25);
}
.infra-item:nth-child(4) .infra-item-icon {
  background: rgb(234 179 8 / 0.14);
  color: #eab308;
}

.infra-item-icon {
  display: grid;
  width: 36px;
  height: 36px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 8px;
}

.infra-item-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.infra-item-text span {
  color: var(--foreground);
  font-size: 13px;
  font-weight: 760;
  white-space: nowrap;
}

.infra-item-text small {
  color: var(--foreground-secondary);
  font-size: 11px;
  font-weight: 600;
}

.topology-handle {
  width: 10px;
  height: 10px;
  border: 2px solid rgb(var(--card-rgb));
  background: currentColor;
  opacity: 1;
}

.topology-card-node.entry .topology-handle {
  color: #0284c7;
}

.topology-card-node.control .topology-handle {
  color: #7c3aed;
}

.topology-card-node.runtime .topology-handle {
  color: #059669;
}

.topology-card-node.storage .topology-handle {
  color: #d97706;
}

.topology-card-node.insight .topology-handle {
  color: #db2777;
}

.topology-card-node.infra .topology-handle {
  color: #64748b;
}

@media (max-width: 900px) {
  .dashboard-topology-header {
    flex-direction: column;
  }

  .dashboard-topology-legends {
    justify-content: flex-start;
    max-width: none;
  }

  .dashboard-topology-canvas-wrap {
    height: 560px;
    margin: 16px;
  }

  .topology-expanded-overlay {
    padding: 12px;
  }

  .topology-expand-button span {
    display: none;
  }

  .topology-download-button span {
    display: none;
  }

  .topology-expanded-legends {
    top: 10px;
    right: 10px;
    width: 190px;
  }
}

</style>
