<script setup lang="ts">
import { computed, type Component } from "vue";
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
  CircleStackIcon,
  CloudIcon,
  CpuChipIcon,
  FolderIcon,
  ServerIcon,
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
  status?: string;
  tone?: string;
  icon: Component;
  handles: {
    leftTarget?: boolean;
    rightSource?: boolean;
    bottomTarget?: boolean;
    topSource?: boolean;
  };
  service?: boolean;
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

function isNetworkSource(source: SourceResource | null): boolean {
  return ["nas", "nfs", "cifs", "s3", "azure", "gcs"].includes(
    source?.resource_type || "",
  );
}

function isObjectRepository(repository: Repository | null): boolean {
  return ["s3", "azure", "gcs"].includes(repository?.repo_type || "");
}

function isOnline(status?: string | null, explicit?: boolean): boolean {
  return explicit === true || status === "online" || status === "active";
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
  if (status === "error") return "bad";
  if (
    status === "pending" ||
    status === "installing" ||
    status === "maintenance"
  ) {
    return "warn";
  }
  return "muted";
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
  if (repositoryIsObject.value) return "Object Repository";
  if (repository.repo_type === "nas" || repository.repo_type === "nfs") {
    return "NAS / NFS Repository";
  }
  return repository.repo_type_display || "Target Repository";
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

const graphNodes = computed<Node<ResourceNodeData>[]>(() => [
  {
    id: "source",
    type: "resource",
    position: { x: 40, y: 132 },
    selectable: false,
    data: {
      kind: "source",
      kicker: "Source",
      title: props.source?.name || "No source selected",
      subtitle: sourceCardTitle.value,
      detail: sourceEndpoint(props.source),
      icon: FolderIcon,
      handles: {
        rightSource: true,
      },
    },
  },
  {
    id: "executor",
    type: "resource",
    position: { x: 500, y: 110 },
    selectable: false,
    data: {
      kind: "executor",
      kicker: executorRole.value,
      title:
        executorProxy.value?.name ||
        resolvedTask.value?.execution_node_name ||
        "Auto placement",
      subtitle: statusText(
        executorProxy.value?.status,
        executorProxy.value?.is_online,
      ),
      detail: proxyEndpoint(executorProxy.value),
      tone: statusTone(
        executorProxy.value?.status,
        executorProxy.value?.is_online,
      ),
      icon: ServerIcon,
      service: true,
      handles: {
        leftTarget: true,
        rightSource: true,
      },
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
      detail: repositoryEndpoint(resolvedRepository.value),
      icon: CircleStackIcon,
      handles: {
        leftTarget: true,
        bottomTarget: true,
      },
    },
  },
  {
    id: "gateway",
    type: "resource",
    position: { x: 960, y: 410 },
    selectable: false,
    data: {
      kind: "gateway",
      kicker: "Gateway Node",
      title: gateway.value?.name || "No Gateway connected",
      subtitle: gateway.value
        ? statusText(gateway.value.status, gateway.value.is_online)
        : "Missing",
      detail:
        gateway.value?.internal_ip ||
        gateway.value?.hostname ||
        "AI Insights reads repository snapshots",
      tone: gateway.value
        ? statusTone(gateway.value.status, gateway.value.is_online)
        : "muted",
      icon: SparklesIcon,
      handles: {
        topSource: true,
      },
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
      fill: "rgba(7, 17, 31, 0.9)",
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
      fill: "rgba(7, 17, 31, 0.9)",
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
      fill: "rgba(7, 17, 31, 0.9)",
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
        <Background :gap="18" :size="1" pattern-color="#1e3a5f" />
        <Controls position="bottom-right" />

        <template #node-resource="{ data }">
          <article :class="['topology-node', data.kind]">
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

            <div :class="['node-icon', data.kind]">
              <component :is="data.icon" class="h-7 w-7" />
            </div>
            <div class="node-copy">
              <p class="node-kicker">{{ data.kicker }}</p>
              <h4>{{ data.title }}</h4>
              <span
                :class="['node-subtitle', data.tone && 'status', data.tone]"
              >
                {{ data.subtitle }}
              </span>
              <small>{{ data.detail }}</small>
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
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 12px;
  background:
    radial-gradient(
      circle at 30% 20%,
      rgba(56, 189, 248, 0.13),
      transparent 28%
    ),
    linear-gradient(135deg, #07111f 0%, #0a1726 100%);
  color: #e5edf8;
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
  color: #9ca9bb;
  font-size: 13px;
}

.flow-badge {
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.6);
  padding: 6px 10px;
  color: #cbd5e1;
  font-size: 12px;
  white-space: nowrap;
}

.flow-canvas {
  position: relative;
  height: 600px;
  margin: 0 20px 16px;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 12px;
  background: rgba(2, 6, 23, 0.14);
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
  stroke: rgba(148, 163, 184, 0.16);
  stroke-width: 1px;
}

:deep(.vue-flow__node-resource) {
  border: none;
  background: transparent;
  box-shadow: none;
}

:deep(.vue-flow__controls) {
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 8px;
  box-shadow: none;
}

:deep(.vue-flow__controls-button) {
  border-color: rgba(148, 163, 184, 0.16);
  background: rgba(15, 23, 42, 0.88);
  color: #cbd5e1;
}

.topology-node {
  position: relative;
  z-index: 5;
  display: flex;
  gap: 14px;
  width: 230px;
  min-height: 128px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 10px;
  background: rgba(15, 28, 45, 0.94);
  padding: 16px;
  box-shadow: 0 14px 30px rgba(2, 6, 23, 0.22);
}

.topology-node.executor {
  min-height: 172px;
}

.topology-node.gateway {
  min-height: 112px;
}

.flow-handle {
  z-index: 10;
  width: 12px;
  height: 12px;
  border: 2px solid rgba(229, 237, 248, 0.92);
  border-radius: 999px;
  background: #38bdf8;
  box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.16);
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
  background: #34d399;
  box-shadow: 0 0 0 3px rgba(52, 211, 153, 0.16);
}

.topology-node.repository .bottom-handle,
.topology-node.gateway .top-handle {
  background: #a78bfa;
  box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.18);
}

.node-icon {
  display: grid;
  flex: 0 0 auto;
  width: 48px;
  height: 48px;
  place-items: center;
  border-radius: 12px;
}

.node-icon.source {
  color: #7dd3fc;
  background: rgba(14, 165, 233, 0.16);
}

.node-icon.executor {
  color: #c4b5fd;
  background: rgba(124, 58, 237, 0.18);
}

.node-icon.repository {
  color: #86efac;
  background: rgba(22, 163, 74, 0.16);
}

.node-icon.gateway {
  color: #f0abfc;
  background: rgba(168, 85, 247, 0.18);
}

.node-copy {
  min-width: 0;
}

.node-kicker {
  color: #94a3b8;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.topology-node h4 {
  margin-top: 4px;
  color: #f8fafc;
  font-size: 14px;
  font-weight: 700;
}

.topology-node span,
.topology-node small {
  display: block;
  margin-top: 6px;
  color: #cbd5e1;
  font-size: 12px;
  line-height: 1.35;
}

.topology-node small {
  max-width: 150px;
  overflow: hidden;
  color: #94a3b8;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status.good {
  color: #86efac;
}

.status.warn {
  color: #facc15;
}

.status.bad {
  color: #fb7185;
}

.status.muted {
  color: #94a3b8;
}

.service-chip {
  position: absolute;
  right: 16px;
  bottom: 14px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 999px;
  background: rgba(2, 6, 23, 0.32);
  padding: 6px 10px;
  color: #e0e7ff;
  font-size: 12px;
}

.flow-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border-top: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(15, 23, 42, 0.34);
}

.flow-summary div {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  border-right: 1px solid rgba(148, 163, 184, 0.16);
  color: #cbd5e1;
  font-size: 12px;
}

.flow-summary div:last-child {
  border-right: none;
}

.compact .flow-canvas {
  margin-bottom: 12px;
}
</style>
