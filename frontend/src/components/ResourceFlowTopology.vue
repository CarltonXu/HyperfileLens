<script setup lang="ts">
import { computed } from "vue";
import {
  Handle,
  MarkerType,
  Position,
  VueFlow,
  type Edge,
  type Node,
} from "@vue-flow/core";
import { Background } from "@vue-flow/background";
import { Controls } from "@vue-flow/controls";
import {
  ArchiveBoxIcon,
  CircleStackIcon,
  CloudIcon,
  ComputerDesktopIcon,
  CpuChipIcon,
  EyeIcon,
  FolderOpenIcon,
  FolderIcon,
  ShieldCheckIcon,
  SparklesIcon,
} from "@heroicons/vue/24/outline";
import "@vue-flow/core/dist/style.css";
import "@vue-flow/core/dist/theme-default.css";
import type { BackupTask } from "@/types/backup";
import type { ProxyNode } from "@/types/proxy";
import type { Repository } from "@/types/repository";
import type { SourceResource } from "@/types/sourceResource";

interface GatewayNode {
  id: string;
  name: string;
  hostname?: string | null;
  internal_ip?: string | null;
  status?: string | null;
  cpu_usage?: number | null;
  memory_usage?: number | null;
  mount_base_path?: string | null;
  is_online?: boolean;
  ai_enabled?: boolean;
  indexer_status?: string | null;
}

interface FlowTopology {
  task?: BackupTask | null;
  repository?: Repository | null;
  executor_proxy?: ProxyNode | null;
  executor_role?: "agent" | "sync" | string | null;
  selection_reason?: string | null;
  gateway?: GatewayNode | null;
  source_is_network?: boolean;
}

interface ResourceNodeData {
  kind: "source" | "executor" | "repository" | "gateway";
  kicker: string;
  title: string;
  subtitle: string;
  detail: string;
  tone?: string;
  icon: any;
  statusIconTone?: string;
  details?: Array<{
    label: string;
    value: string;
    wrap?: boolean;
    status?: boolean;
  }>;
  handles: {
    leftTarget?: boolean;
    rightSource?: boolean;
    bottomTarget?: boolean;
    topSource?: boolean;
  };
  service?: boolean;
  viewUrl?: string;
}

const props = withDefaults(
  defineProps<{
    source: SourceResource | null;
    task?: BackupTask | null;
    repository?: Repository | null;
    proxies?: ProxyNode[];
    gateways?: GatewayNode[];
    topology?: FlowTopology | null;
    compact?: boolean;
  }>(),
  {
    task: null,
    repository: null,
    proxies: () => [],
    gateways: () => [],
    topology: null,
    compact: false,
  },
);

function openNodeDetail(node: ResourceNodeData) {
  if (!node.viewUrl) return;
  window.open(node.viewUrl, "_blank", "noopener,noreferrer");
}

function detailUrl(
  path: string,
  id?: string | number | null,
): string | undefined {
  if (!id) return undefined;
  return `${path}?detail=${encodeURIComponent(String(id))}`;
}

function isNetworkSource(source: SourceResource | null): boolean {
  return ["nas", "nfs", "cifs", "s3", "azure", "gcs"].includes(
    source?.resource_type || "",
  );
}

function isObjectRepository(repository: Repository | null): boolean {
  return ["s3", "azure", "gcs"].includes(repository?.repo_type || "");
}

function isOnline(status?: string | null, explicit?: boolean): boolean {
  return (
    explicit === true ||
    status === "online" ||
    status === "active" ||
    status === "connected" ||
    status === "mounted"
  );
}

function statusText(status?: string | null, explicit?: boolean): string {
  if (isOnline(status, explicit)) return "Online";
  if (status === "pending" || status === "installing") return "Pending";
  if (status === "maintenance") return "Maintenance";
  if (status === "error") return "Error";
  return status || "Unknown";
}

function statusTone(status?: string | null, explicit?: boolean): string {
  if (isOnline(status, explicit)) return "good";
  if (
    status === "error" ||
    status === "offline" ||
    status === "inactive" ||
    status === "disconnected"
  ) {
    return "bad";
  }
  if (
    status === "pending" ||
    status === "installing" ||
    status === "maintenance"
  ) {
    return "warn";
  }
  return "muted";
}

function formatBytes(value?: number | null): string {
  if (!value || value <= 0) return "-";
  const units = ["B", "KB", "MB", "GB", "TB", "PB"];
  let size = value;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  const precision = size >= 10 || unitIndex === 0 ? 0 : 1;
  return `${size.toFixed(precision)} ${units[unitIndex]}`;
}

function formatPercent(value?: number | null): string {
  return value == null ? "-" : `${value.toFixed(0)}%`;
}

function proxyEndpoint(proxy: ProxyNode | null): string {
  if (!proxy) return "No proxy selected";
  return (
    proxy.internal_ip || proxy.connection_ip || proxy.hostname || proxy.name
  );
}

function sourceEndpoint(source: SourceResource | null): string {
  if (!source) return "-";
  const config = source.config || {};
  if (source.resource_type === "local") {
    return config.root_path || config.path || source.mount_point || source.name;
  }
  if (source.resource_type === "nfs" || source.resource_type === "nas") {
    return (
      [config.server, config.export_path].filter(Boolean).join(":") ||
      source.name
    );
  }
  if (source.resource_type === "cifs") {
    return (
      [config.server, config.share].filter(Boolean).join("/") || source.name
    );
  }
  if (source.resource_type === "s3") {
    return (
      [config.endpoint, config.bucket, config.prefix]
        .filter(Boolean)
        .join(" / ") || source.name
    );
  }
  return source.name;
}

function sourceTopologyType(source: SourceResource | null): string {
  if (!source) return "Source Resource";
  if (source.resource_type === "local") return "Filesystem";
  if (["nas", "nfs", "cifs"].includes(source.resource_type)) {
    return "NAS/NFS/CIFS";
  }
  if (["s3", "azure", "gcs"].includes(source.resource_type)) {
    return "Object Storage";
  }
  return source.resource_type_display || source.resource_type.toUpperCase();
}

function sourceSharedPath(source: SourceResource | null): string {
  if (!source) return "-";
  const config = source.config || {};
  if (source.resource_type === "local") {
    return config.root_path || config.path || source.mount_point || "-";
  }
  if (source.resource_type === "nas" || source.resource_type === "nfs") {
    return (
      [config.server, config.export_path].filter(Boolean).join(":") ||
      source.name
    );
  }
  if (source.resource_type === "cifs") {
    return (
      [config.server, config.share].filter(Boolean).join("/") || source.name
    );
  }
  return sourceEndpoint(source);
}

function sourceCapacity(source: SourceResource | null): string {
  if (!source) return "-";
  const used = formatBytes(source.used_size);
  const total = formatBytes(source.total_size);
  if (used !== "-" && total !== "-") return `${used} / ${total}`;
  if (used !== "-") return used;
  if (total !== "-") return total;
  return "-";
}

function sourceAvailability(source: SourceResource | null): string {
  if (!source) return "Unknown";
  if (source.status_display) return source.status_display;
  if (source.status === "active" || source.status === "connected") {
    return "Available";
  }
  if (source.status === "inactive" || source.status === "disconnected") {
    return "Offline";
  }
  if (source.status === "error") return "Error";
  return source.status || "Unknown";
}

function sourceLocalAddress(source: SourceResource | null): string {
  if (!source) return "-";
  return (
    boundSourceProxy.value?.internal_ip ||
    boundSourceProxy.value?.connection_ip ||
    source.bound_node?.hostname ||
    "-"
  );
}

function backupPath(source: SourceResource | null): string {
  if (!source) return "-";
  return source.mount_point || sourceSharedPath(source);
}

function backupRepositoryPath(repository: Repository | null): string {
  if (!repository) return "-";
  const config = repository.config || {};
  if (repository.repo_type === "s3") {
    return config.bucket || repository.name;
  }
  if (repository.repo_type === "azure") {
    return config.container || repository.name;
  }
  if (repository.repo_type === "gcs") {
    return config.bucket_name || config.bucket || repository.name;
  }
  if (repository.repo_type === "local") {
    return config.path || repository.name;
  }
  if (repository.repo_type === "nas" || repository.repo_type === "nfs") {
    return `/mnt/hyperfilelens/repository-${repository.id.slice(0, 8)}`;
  }
  return repositorySharedPath(repository);
}

function sourceIcon(source: SourceResource | null): any {
  if (!source) return FolderIcon;
  if (source.resource_type === "local") return ComputerDesktopIcon;
  if (["nas", "nfs", "cifs"].includes(source.resource_type)) {
    return FolderOpenIcon;
  }
  if (["s3", "azure", "gcs"].includes(source.resource_type)) return CloudIcon;
  return FolderIcon;
}

function repositoryEndpoint(repository: Repository | null): string {
  if (!repository) return "No repository selected";
  const config = repository.config || {};
  if (repository.repo_type === "local") return config.path || repository.name;
  if (repository.repo_type === "nas" || repository.repo_type === "nfs") {
    return (
      [config.server, config.export_path].filter(Boolean).join(":") ||
      repository.name
    );
  }
  if (repository.repo_type === "s3") {
    return (
      [config.endpoint, config.bucket, config.prefix]
        .filter(Boolean)
        .join(" / ") || repository.name
    );
  }
  return repository.name;
}

function repositoryTypeLabel(repository: Repository | null): string {
  if (!repository) return "Target Repository";
  if (repository.repo_type === "nas" || repository.repo_type === "nfs") {
    const nasType = repository.config?.nas_type?.toUpperCase();
    return nasType ? `NAS / ${nasType}` : "NAS / NFS";
  }
  if (repository.repo_type === "s3") return "S3 Object Storage";
  if (repository.repo_type === "azure") return "Azure Blob";
  if (repository.repo_type === "gcs") return "Google Cloud Storage";
  if (repository.repo_type === "local") return "Local Repository";
  return repository.repo_type_display || "Target Repository";
}

function repositoryTopologyType(repository: Repository | null): string {
  if (!repository) return "Target Repository";
  if (repository.repo_type === "nas" || repository.repo_type === "nfs") {
    return "NAS/NFS/CIFS";
  }
  if (["s3", "azure", "gcs"].includes(repository.repo_type)) {
    return "Object Storage";
  }
  if (repository.repo_type === "local") return "Local Filesystem";
  return repository.repo_type_display || repository.repo_type.toUpperCase();
}

function repositorySharedPath(repository: Repository | null): string {
  if (!repository) return "-";
  const config = repository.config || {};
  if (repository.repo_type === "nas" || repository.repo_type === "nfs") {
    return (
      [config.server, config.export_path].filter(Boolean).join(":") ||
      config.path ||
      repository.name
    );
  }
  if (repository.repo_type === "s3") {
    return (
      [config.endpoint, config.bucket, config.prefix]
        .filter(Boolean)
        .join(" / ") || repository.name
    );
  }
  if (repository.repo_type === "azure") {
    return (
      [config.account_name, config.container, config.prefix]
        .filter(Boolean)
        .join(" / ") || repository.name
    );
  }
  if (repository.repo_type === "gcs") {
    return (
      [config.project_id, config.bucket_name || config.bucket, config.prefix]
        .filter(Boolean)
        .join(" / ") || repository.name
    );
  }
  if (repository.repo_type === "local") return config.path || repository.name;
  return repositoryEndpoint(repository);
}

function repositoryCapacity(repository: Repository | null): string {
  if (!repository) return "-";
  const used = repository.used_space_formatted;
  const total =
    repository.capacity_formatted || repository.quota_bytes_formatted;
  if (used && total) return `${used} / ${total}`;
  if (used) return used;
  if (total) return total;
  return "-";
}

function repositoryAvailability(repository: Repository | null): string {
  if (!repository) return "Unavailable";
  if (repository.status_display) return repository.status_display;
  if (repository.status === "active") return "Available";
  if (repository.status === "initializing") return "Initializing";
  if (repository.status === "maintenance") return "Maintenance";
  if (repository.status === "error") return "Error";
  return repository.status || "Unknown";
}

function repositoryIcon(repository: Repository | null): any {
  if (!repository) return CircleStackIcon;
  if (repository.repo_type === "nas" || repository.repo_type === "nfs") {
    return FolderOpenIcon;
  }
  if (["s3", "azure", "gcs"].includes(repository.repo_type)) return CloudIcon;
  if (repository.repo_type === "local") return ArchiveBoxIcon;
  return CircleStackIcon;
}

function findProxyById(id?: string | null): ProxyNode | null {
  if (!id) return null;
  return props.proxies.find((proxy) => proxy.id === id) || null;
}

const sourceIsNetwork = computed(() => isNetworkSource(props.source));
const resolvedRepository = computed(
  () => props.topology?.repository || props.repository || null,
);
const resolvedTask = computed(() => props.topology?.task || props.task || null);
const repositoryIsObject = computed(() =>
  isObjectRepository(resolvedRepository.value),
);

const boundSourceProxy = computed(() => {
  const id = props.source?.bound_node?.id || null;
  return findProxyById(id);
});

const boundRepositoryProxy = computed(() => {
  const id = resolvedRepository.value?.bound_node || null;
  return findProxyById(id);
});

const preferredTaskProxy = computed(() =>
  findProxyById(resolvedTask.value?.preferred_execution_node || null),
);

const executorProxy = computed(() => {
  if (props.topology?.executor_proxy) return props.topology.executor_proxy;
  if (preferredTaskProxy.value) return preferredTaskProxy.value;
  if (sourceIsNetwork.value) {
    return (
      boundSourceProxy.value ||
      boundRepositoryProxy.value ||
      props.proxies.find((proxy) => proxy.role === "sync") ||
      null
    );
  }
  return (
    boundSourceProxy.value ||
    props.proxies.find((proxy) => proxy.role === "agent") ||
    boundRepositoryProxy.value ||
    null
  );
});

const gateway = computed(
  () =>
    props.topology?.gateway ||
    props.gateways.find(
      (item) =>
        item.ai_enabled !== false && isOnline(item.status, item.is_online),
    ) ||
    props.gateways[0] ||
    null,
);

const executorRole = computed(() => {
  if (props.topology?.executor_role === "agent") return "Agent Proxy";
  if (props.topology?.executor_role === "sync") return "Sync Proxy";
  if (executorProxy.value?.role === "agent") return "Agent Proxy";
  if (executorProxy.value?.role === "sync") return "Sync Proxy";
  return sourceIsNetwork.value ? "Sync Proxy" : "Agent Proxy";
});

const sourceCardTitle = computed(() => {
  if (!props.source) return "Backup Source";
  if (!sourceIsNetwork.value && executorProxy.value?.role === "agent") {
    return "Source Path";
  }
  return (
    props.source.resource_type_display ||
    props.source.resource_type.toUpperCase()
  );
});

const repositoryCardTitle = computed(() => {
  const repository = resolvedRepository.value;
  if (!repository) return "Target Repository";
  return repositoryTypeLabel(repository);
});

const scenarioText = computed(() => {
  if (sourceIsNetwork.value && repositoryIsObject.value) {
    return "Network source is read by Sync Proxy and written to object storage.";
  }
  if (!sourceIsNetwork.value && executorProxy.value?.role === "agent") {
    return "Agent Proxy reads the local source and writes directly to the target repository.";
  }
  return "Executor Proxy reads the source and writes backup snapshots to the target repository.";
});

const sourceHasDetails = computed(() =>
  ["local", "nas", "nfs", "cifs"].includes(props.source?.resource_type || ""),
);

const graphNodes = computed<Node<ResourceNodeData>[]>(() => [
  {
    id: "source",
    type: "resource",
    position: { x: 40, y: sourceHasDetails.value ? 132 : 165 },
    selectable: false,
    data: {
      kind: "source",
      kicker: "Source",
      title: props.source?.name || "No source selected",
      subtitle: sourceCardTitle.value,
      detail: sourceSharedPath(props.source),
      tone: statusTone(props.source?.status),
      icon: sourceIcon(props.source),
      details:
        props.source?.resource_type === "local"
          ? [
              {
                label: "Type",
                value: "Filesystem",
              },
              {
                label: "IP",
                value: sourceLocalAddress(props.source),
              },
              {
                label: "Path",
                value: sourceSharedPath(props.source),
                wrap: true,
              },
              {
                label: "Capacity",
                value: sourceCapacity(props.source),
              },
              {
                label: "Status",
                value: sourceAvailability(props.source),
                status: true,
              },
            ]
          : ["nas", "nfs", "cifs"].includes(props.source?.resource_type || "")
            ? [
                {
                  label: "Type",
                  value: sourceTopologyType(props.source),
                },
                {
                  label: "Shared Path",
                  value: sourceSharedPath(props.source),
                  wrap: true,
                },
                {
                  label: "Capacity",
                  value: sourceCapacity(props.source),
                },
                {
                  label: "Status",
                  value: sourceAvailability(props.source),
                  status: true,
                },
              ]
            : undefined,
      handles: {
        rightSource: true,
      },
      viewUrl: detailUrl("/source-resources", props.source?.id),
    },
  },
  {
    id: "executor",
    type: "resource",
    position: { x: 500, y: 86 },
    selectable: false,
    data: {
      kind: "executor",
      kicker: executorRole.value,
      title:
        executorProxy.value?.name ||
        resolvedTask.value?.execution_node_name ||
        "Auto placement",
      subtitle: proxyEndpoint(executorProxy.value),
      detail: statusText(
        executorProxy.value?.status,
        executorProxy.value?.is_online,
      ),
      tone: statusTone(
        executorProxy.value?.status,
        executorProxy.value?.is_online,
      ),
      icon: ComputerDesktopIcon,
      statusIconTone: statusTone(
        executorProxy.value?.status,
        executorProxy.value?.is_online,
      ),
      service: true,
      details: [
        {
          label: "IP",
          value: proxyEndpoint(executorProxy.value),
        },
        {
          label: "CPU",
          value: formatPercent(executorProxy.value?.cpu_usage),
        },
        {
          label: "MEM",
          value: formatPercent(executorProxy.value?.memory_usage),
        },
        {
          label: "Status",
          value: statusText(
            executorProxy.value?.status,
            executorProxy.value?.is_online,
          ),
          status: true,
        },
        {
          label: "S-PATH",
          value: backupPath(props.source),
          wrap: true,
        },
        {
          label: "T-PATH",
          value: backupRepositoryPath(resolvedRepository.value),
          wrap: true,
        },
      ],
      handles: {
        leftTarget: true,
        rightSource: true,
      },
      viewUrl: executorProxy.value?.id
        ? detailUrl("/proxies", executorProxy.value.id)
        : undefined,
    },
  },
  {
    id: "repository",
    type: "resource",
    position: { x: 960, y: 132 },
    selectable: false,
    data: {
      kind: "repository",
      kicker: "Target",
      title:
        resolvedRepository.value?.name ||
        resolvedTask.value?.target_repository_name ||
        "No repository selected",
      subtitle: repositoryCardTitle.value,
      detail: repositorySharedPath(resolvedRepository.value),
      tone: statusTone(resolvedRepository.value?.status),
      icon: repositoryIcon(resolvedRepository.value),
      details: [
        {
          label: "Type",
          value: repositoryTopologyType(resolvedRepository.value),
        },
        {
          label:
            resolvedRepository.value?.repo_type === "local"
              ? "Path"
              : ["s3", "azure", "gcs"].includes(
                    resolvedRepository.value?.repo_type || "",
                  )
                ? "Endpoint"
                : "Shared Path",
          value: repositorySharedPath(resolvedRepository.value),
          wrap: true,
        },
        {
          label: "Capacity",
          value: repositoryCapacity(resolvedRepository.value),
        },
        {
          label: "Status",
          value: repositoryAvailability(resolvedRepository.value),
          status: true,
        },
      ],
      handles: {
        leftTarget: true,
        bottomTarget: true,
      },
      viewUrl: detailUrl("/repository", resolvedRepository.value?.id),
    },
  },
  {
    id: "gateway",
    type: "resource",
    position: { x: 950, y: 470 },
    selectable: false,
    data: {
      kind: "gateway",
      kicker: "Gateway Node",
      title: gateway.value?.name || "No Gateway connected",
      subtitle:
        gateway.value?.internal_ip ||
        gateway.value?.hostname ||
        "AI Insights reads repository snapshots",
      detail: gateway.value
        ? statusText(gateway.value.status, gateway.value.is_online)
        : "Missing",
      tone: gateway.value
        ? statusTone(gateway.value.status, gateway.value.is_online)
        : "bad",
      icon: SparklesIcon,
      details: [
        {
          label: "IP",
          value: gateway.value?.internal_ip || gateway.value?.hostname || "-",
        },
        {
          label: "CPU",
          value: formatPercent(gateway.value?.cpu_usage),
        },
        {
          label: "MEM",
          value: formatPercent(gateway.value?.memory_usage),
        },
        {
          label: "Status",
          value: gateway.value
            ? statusText(gateway.value.status, gateway.value.is_online)
            : "Offline",
          status: true,
        },
      ],
      handles: {
        topSource: true,
      },
      viewUrl: detailUrl("/gateways", gateway.value?.id),
    },
  },
]);

const graphEdges = computed<Edge[]>(() => [
  {
    id: "source-executor",
    source: "source",
    target: "executor",
    sourceHandle: "right",
    targetHandle: "left",
    label: "read source",
    type: "smoothstep",
    animated: true,
    markerEnd: MarkerType.ArrowClosed,
    style: {
      stroke: "#38bdf8",
      strokeWidth: 2.5,
    },
    labelStyle: {
      fill: "#7dd3fc",
      fontWeight: 700,
    },
    labelBgStyle: {
      fill: "var(--topology-label-bg)",
    },
  },
  {
    id: "executor-repository",
    source: "executor",
    target: "repository",
    sourceHandle: "right",
    targetHandle: "left",
    label: "write snapshots",
    type: "smoothstep",
    animated: true,
    markerEnd: MarkerType.ArrowClosed,
    style: {
      stroke: "#34d399",
      strokeWidth: 2.5,
    },
    labelStyle: {
      fill: "#86efac",
      fontWeight: 700,
    },
    labelBgStyle: {
      fill: "var(--topology-label-bg)",
    },
  },
  {
    id: "gateway-repository",
    source: "gateway",
    target: "repository",
    sourceHandle: "top",
    targetHandle: "bottom",
    label: "AI Insights",
    type: "smoothstep",
    animated: true,
    markerEnd: MarkerType.ArrowClosed,
    style: {
      stroke: "#a78bfa",
      strokeWidth: 2.5,
    },
    labelStyle: {
      fill: "#c4b5fd",
      fontWeight: 700,
    },
    labelBgStyle: {
      fill: "var(--topology-label-bg)",
    },
  },
]);
</script>

<template>
  <section class="flow-topology" :class="{ compact }">
    <div class="flow-header">
      <div>
        <h3>Data Flow Topology</h3>
        <p>{{ scenarioText }}</p>
      </div>
      <div class="flow-badge">
        {{ task ? "Backup Task" : "Source Resource" }}
      </div>
    </div>

    <div class="flow-canvas">
      <VueFlow
        :nodes="graphNodes"
        :edges="graphEdges"
        :nodes-draggable="true"
        :nodes-connectable="false"
        :edges-updatable="false"
        :elements-selectable="false"
        :pan-on-drag="true"
        :zoom-on-scroll="true"
        :zoom-on-pinch="true"
        :min-zoom="0.6"
        :max-zoom="1.4"
        fit-view-on-init
        class="resource-flow"
      >
        <Background :gap="18" :size="1" pattern-color="var(--topology-grid)" />
        <Controls position="bottom-right" />

        <template #node-resource="{ data }">
          <article
            :class="[
              'topology-node',
              data.kind,
              { 'has-details': data.details?.length },
            ]"
          >
            <Handle
              v-if="data.handles.leftTarget"
              id="left"
              type="target"
              :position="Position.Left"
              class="flow-handle left-handle"
            />
            <Handle
              v-if="data.handles.rightSource"
              id="right"
              type="source"
              :position="Position.Right"
              class="flow-handle right-handle"
            />
            <Handle
              v-if="data.handles.bottomTarget"
              id="bottom"
              type="target"
              :position="Position.Bottom"
              class="flow-handle bottom-handle"
            />
            <Handle
              v-if="data.handles.topSource"
              id="top"
              type="source"
              :position="Position.Top"
              class="flow-handle top-handle"
            />

            <button
              v-if="data.viewUrl"
              class="node-view-button"
              type="button"
              title="View resource details"
              @click.stop="openNodeDetail(data)"
            >
              <EyeIcon class="h-3.5 w-3.5" />
              View
            </button>

            <div :class="['node-icon', data.kind]">
              <component :is="data.icon" class="h-7 w-7" />
              <span
                v-if="data.kind === 'executor'"
                :class="['proxy-shield', data.statusIconTone]"
              >
                <ShieldCheckIcon class="shield-base" />
              </span>
            </div>
            <div class="node-copy">
              <p class="node-kicker">{{ data.kicker }}</p>
              <h4>{{ data.title }}</h4>
              <span
                v-if="data.kind !== 'repository' && !data.details?.length"
                class="node-subtitle"
              >
                {{ data.subtitle }}
              </span>
              <small
                v-if="!data.details?.length"
                :class="
                  ['executor', 'gateway'].includes(data.kind) ? data.tone : ''
                "
              >
                {{ data.detail }}
              </small>
            </div>
            <div v-if="data.details?.length" class="repository-details">
              <div
                v-for="item in data.details"
                :key="item.label"
                :class="['repository-detail', { wrap: item.wrap }]"
              >
                <span>{{ item.label }}:</span>
                <strong v-if="!item.status">{{ item.value }}</strong>
                <strong v-else :class="['repository-status', data.tone]">
                  <CircleStackIcon class="h-3.5 w-3.5" />
                  {{ item.value }}
                </strong>
              </div>
            </div>
            <div v-if="data.service" class="service-chip">
              <CpuChipIcon class="h-4 w-4" />
              Backup Service
            </div>
          </article>
        </template>
      </VueFlow>
    </div>

    <div class="flow-summary">
      <div>
        <CloudIcon class="h-5 w-5" />
        <span>Execution: {{ executorRole }}</span>
      </div>
      <div>
        <CircleStackIcon class="h-5 w-5" />
        <span
          >Repository:
          {{
            resolvedRepository?.repo_type_display ||
            resolvedRepository?.repo_type ||
            "-"
          }}</span
        >
      </div>
      <div>
        <SparklesIcon class="h-5 w-5" />
        <span>Gateway: {{ gateway ? "available" : "not connected" }}</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.flow-topology {
  --topology-surface: rgb(var(--card-rgb) / 0.96);
  --topology-surface-soft: rgb(var(--background-secondary-rgb) / 0.92);
  --topology-canvas: rgb(var(--background-secondary-rgb) / 0.58);
  --topology-node: rgb(var(--card-rgb) / 0.98);
  --topology-node-highlight: rgb(255 255 255 / 0.82);
  --topology-border: rgb(var(--border-rgb) / 0.92);
  --topology-border-soft: rgb(var(--border-rgb) / 0.72);
  --topology-text: var(--foreground);
  --topology-text-secondary: var(--foreground-secondary);
  --topology-text-muted: var(--foreground-tertiary);
  --topology-label-bg: rgb(var(--card-rgb) / 0.94);
  --topology-grid: rgb(var(--border-rgb) / 0.72);
  --topology-shadow: 0 16px 34px rgb(15 23 42 / 0.1);
  --topology-icon-shadow: 0 10px 26px rgb(15 23 42 / 0.12);
  --topology-control-bg: rgb(var(--card-rgb) / 0.96);
  --topology-control-hover: var(--hover);
  --topology-source: #0284c7;
  --topology-source-soft: rgb(14 165 233 / 0.12);
  --topology-repo: var(--success);
  --topology-repo-soft: rgb(var(--success-rgb) / 0.13);
  --topology-ai: #8b5cf6;
  --topology-ai-soft: rgb(139 92 246 / 0.14);
  overflow: hidden;
  border: 1px solid var(--topology-border);
  border-radius: 12px;
  background:
    radial-gradient(
      circle at 30% 20%,
      rgb(var(--primary-rgb) / 0.1),
      transparent 28%
    ),
    linear-gradient(
      135deg,
      var(--topology-surface) 0%,
      var(--topology-surface-soft) 100%
    );
  color: var(--topology-text);
}

:global(.dark) .flow-topology {
  --topology-surface: rgb(var(--card-rgb) / 0.96);
  --topology-surface-soft: rgb(var(--background-secondary-rgb) / 0.94);
  --topology-canvas: rgb(2 6 23 / 0.16);
  --topology-node: rgb(var(--background-secondary-rgb) / 0.95);
  --topology-node-highlight: rgb(255 255 255 / 0.08);
  --topology-border: rgb(var(--border-rgb) / 0.95);
  --topology-border-soft: rgb(var(--border-rgb) / 0.78);
  --topology-label-bg: rgb(var(--background-secondary-rgb) / 0.95);
  --topology-grid: rgb(var(--border-secondary-rgb) / 0.58);
  --topology-shadow: 0 16px 34px rgb(0 0 0 / 0.26);
  --topology-icon-shadow: 0 12px 28px rgb(0 0 0 / 0.34);
  --topology-control-bg: rgb(var(--background-secondary-rgb) / 0.96);
  --topology-control-hover: var(--hover-secondary);
  --topology-source: #7dd3fc;
  --topology-source-soft: rgb(14 165 233 / 0.16);
  --topology-ai: #c4b5fd;
  --topology-ai-soft: rgb(168 85 247 / 0.18);
}

.flow-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px 8px;
}

.flow-header h3 {
  font-size: 16px;
  font-weight: 700;
}

.flow-header p {
  margin-top: 4px;
  color: var(--topology-text-secondary);
  font-size: 13px;
}

.flow-badge {
  border: 1px solid var(--topology-border-soft);
  border-radius: 999px;
  background: rgb(var(--background-rgb) / 0.62);
  padding: 6px 10px;
  color: var(--topology-text-secondary);
  font-size: 12px;
  white-space: nowrap;
}

.flow-canvas {
  position: relative;
  height: 600px;
  margin: 0 20px 16px;
  overflow: hidden;
  border: 1px solid var(--topology-border-soft);
  border-radius: 12px;
  background: var(--topology-canvas);
}

.resource-flow {
  width: 100%;
  height: 100%;
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
  stroke-dasharray: 8 10;
  animation-duration: 1.4s;
}

:deep(.vue-flow__edge-textbg) {
  rx: 4px;
  ry: 4px;
  stroke: var(--topology-border-soft);
  stroke-width: 1px;
}

:deep(.vue-flow__node-resource) {
  border: none;
  background: transparent;
  box-shadow: none;
}

:deep(.vue-flow__controls) {
  overflow: hidden;
  border: 1px solid var(--topology-border);
  border-radius: 8px;
  box-shadow: none;
}

:deep(.vue-flow__controls-button) {
  border-color: var(--topology-border-soft);
  background: var(--topology-control-bg);
  color: var(--topology-text-secondary);
}

:deep(.vue-flow__controls-button:hover) {
  background: var(--topology-control-hover);
  color: var(--topology-text);
}

.topology-node {
  position: relative;
  z-index: 5;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 12px;
  width: 210px;
  height: auto;
  border: 1px solid var(--topology-border);
  border-radius: 10px;
  background: var(--topology-node);
  padding: 14px;
  box-shadow: var(--topology-shadow);
}

.topology-node.source.has-details {
  width: 268px;
}

.topology-node.executor.has-details,
.topology-node.gateway.has-details {
  width: 278px;
}

.topology-node.repository {
  width: 268px;
}

.node-view-button {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 12;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid var(--topology-border-soft);
  border-radius: 999px;
  background: rgb(var(--card-rgb) / 0.92);
  padding: 4px 8px;
  color: var(--topology-text-secondary);
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
  opacity: 0;
  box-shadow: 0 8px 18px rgb(15 23 42 / 0.12);
  transition:
    opacity 0.16s ease,
    transform 0.16s ease,
    color 0.16s ease,
    background 0.16s ease;
  transform: translateY(-2px);
}

.topology-node:hover .node-view-button,
.node-view-button:focus-visible {
  opacity: 1;
  transform: translateY(0);
}

.node-view-button:hover {
  background: rgb(var(--primary-rgb) / 0.12);
  color: var(--primary);
}

.flow-handle {
  z-index: 10;
  width: 12px;
  height: 12px;
  border: 2px solid var(--topology-node);
  border-radius: 999px;
  background: var(--topology-source);
  box-shadow: 0 0 0 3px rgb(56 189 248 / 0.16);
}

.right-handle,
.left-handle {
  top: 50%;
}

.right-handle {
  right: -6px;
}

.left-handle {
  left: -6px;
}

.bottom-handle {
  bottom: -6px;
}

.top-handle {
  top: -6px;
}

.topology-node.executor .right-handle,
.topology-node.repository .left-handle {
  background: var(--topology-repo);
  box-shadow: 0 0 0 3px rgb(var(--success-rgb) / 0.16);
}

.topology-node.repository .bottom-handle,
.topology-node.gateway .top-handle {
  background: var(--topology-ai);
  box-shadow: 0 0 0 3px rgb(167 139 250 / 0.18);
}

.node-icon {
  position: relative;
  display: grid;
  align-self: start;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 12px;
}

.node-icon :deep(svg) {
  width: 25px;
  height: 25px;
}

.node-icon.source {
  color: var(--topology-source);
  background: var(--topology-source-soft);
}

.node-icon.executor {
  color: var(--topology-source);
  background: var(--topology-source-soft);
}

.node-icon.repository {
  color: var(--topology-repo);
  background: var(--topology-repo-soft);
}

.node-icon.gateway {
  color: var(--topology-ai);
  background: var(--topology-ai-soft);
}

.node-copy {
  min-width: 0;
  overflow: hidden;
}

.proxy-shield {
  position: absolute;
  right: -5px;
  bottom: -5px;
  display: grid;
  width: 22px;
  height: 22px;
  place-items: center;
  color: var(--success);
}

.proxy-shield.bad,
.proxy-shield.muted {
  color: var(--danger);
}

.proxy-shield.warn {
  color: var(--warning);
}

.shield-base {
  position: absolute;
  inset: 0;
  width: 22px;
  height: 22px;
  fill: currentColor;
  stroke: var(--topology-node);
  stroke-width: 1.8;
}

.node-kicker {
  color: var(--topology-text-muted);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.topology-node h4 {
  margin-top: 4px;
  color: var(--topology-text);
  font-size: 14px;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-subtitle,
.topology-node small {
  display: block;
  margin-top: 6px;
  color: var(--topology-text-secondary);
  font-size: 12px;
  line-height: 1.35;
}

.topology-node.executor small.good,
.topology-node.gateway small.good {
  color: var(--success);
  font-weight: 700;
}

.topology-node.executor small.bad,
.topology-node.executor small.muted,
.topology-node.gateway small.bad,
.topology-node.gateway small.muted {
  color: var(--danger);
  font-weight: 700;
}

.topology-node.executor small.warn,
.topology-node.gateway small.warn {
  color: var(--warning);
  font-weight: 700;
}

.topology-node small {
  max-width: 150px;
  overflow: hidden;
  color: var(--topology-text-muted);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.topology-node.repository small {
  display: none;
}

.repository-details {
  grid-column: 1 / -1;
  display: grid;
  gap: 6px;
  margin-top: 2px;
  padding-top: 10px;
  border-top: 1px solid var(--topology-border-soft);
}

.repository-detail {
  display: grid;
  grid-template-columns: minmax(72px, max-content) minmax(0, 1fr);
  gap: 8px;
  align-items: start;
  color: var(--topology-text-secondary);
  font-size: 11px;
  line-height: 1.35;
}

.repository-detail span {
  color: var(--topology-text-muted);
  white-space: nowrap;
}

.repository-detail strong {
  overflow: hidden;
  color: var(--topology-text-secondary);
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.repository-detail.wrap strong {
  overflow-wrap: anywhere;
  text-overflow: initial;
  white-space: normal;
}

.repository-status {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.repository-status.good {
  color: var(--success);
}

.repository-status.warn {
  color: var(--warning);
}

.repository-status.bad {
  color: var(--danger);
}

.repository-status.muted {
  color: var(--topology-text-muted);
}

.service-chip {
  grid-column: 1 / -1;
  justify-self: start;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: -4px;
  border: 1px solid var(--topology-border-soft);
  border-radius: 999px;
  background: rgb(var(--background-rgb) / 0.58);
  padding: 6px 10px;
  color: var(--topology-text-secondary);
  font-size: 12px;
}

.flow-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border-top: 1px solid var(--topology-border-soft);
  background: rgb(var(--background-secondary-rgb) / 0.58);
}

.flow-summary div {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  border-right: 1px solid var(--topology-border-soft);
  color: var(--topology-text-secondary);
  font-size: 12px;
}

.flow-summary div:last-child {
  border-right: none;
}

.compact .flow-canvas {
  margin-bottom: 12px;
}
</style>
