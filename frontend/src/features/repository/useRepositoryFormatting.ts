import type { Component, Ref } from "vue";
import {
  CircleStackIcon,
  CloudIcon,
  FolderIcon,
  ServerIcon,
} from "@heroicons/vue/24/outline";
import type { ProxyNode } from "@/types/proxy";

type Translate = (key: string, params?: Record<string, any>) => string;

export function useRepositoryFormatting(t: Translate, nodes: Ref<ProxyNode[]>) {
  function formatBytes(bytes: number): string {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB", "TB", "PB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  }

  function getProgressColor(quotaStatus: string): string {
    if (quotaStatus === "disabled" || quotaStatus === "unlimited") {
      return "bg-gradient-to-r from-blue-500 to-cyan-500";
    }

    switch (quotaStatus) {
      case "critical":
        return "bg-gradient-to-r from-red-500 to-red-600";
      case "warning":
        return "bg-gradient-to-r from-amber-500 to-orange-500";
      case "ok":
        return "bg-gradient-to-r from-blue-500 to-cyan-500";
      default:
        return "bg-gradient-to-r from-blue-500 to-cyan-500";
    }
  }

  function getRepoTypeIcon(type: string): Component {
    const icons: Record<string, Component> = {
      s3: CloudIcon,
      local: FolderIcon,
      nas: ServerIcon,
      nfs: ServerIcon,
      azure: CloudIcon,
      gcs: CloudIcon,
    };
    return icons[type] || CircleStackIcon;
  }

  function getRepoTypeColor(type: string): string {
    const colors: Record<string, string> = {
      s3: "bg-orange-100 text-orange-600",
      local: "bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400",
      nas: "bg-purple-100 text-purple-600",
      nfs: "bg-purple-100 text-purple-600",
      azure: "bg-sky-100 text-sky-600",
      gcs: "bg-red-100 text-red-600",
    };
    return colors[type] || "bg-background-tertiary/50 text-foreground-secondary";
  }

  function getRepoTypeLabel(type: string | undefined | null): string {
    if (!type) return "-";
    const labels: Record<string, string> = {
      s3: "S3",
      local: t("repository.types.local"),
      nas: "NAS",
      nfs: "NFS",
      azure: "Azure",
      gcs: "GCS",
    };
    return labels[type] || type?.toUpperCase() || "-";
  }

  function getNodeName(nodeId: string | null | undefined): string {
    if (!nodeId) return t("sourceResources.noBoundNode");
    const node = nodes.value.find((n) => String(n.id) === nodeId);
    return node?.name || nodeId;
  }

  function getNode(nodeId: string | null | undefined): ProxyNode | undefined {
    if (!nodeId) return undefined;
    return nodes.value.find((n) => String(n.id) === nodeId);
  }

  function getNodeStatus(nodeId: string | null | undefined): string {
    const node = getNode(nodeId);
    return node?.status || "unknown";
  }

  return {
    formatBytes,
    getProgressColor,
    getRepoTypeIcon,
    getRepoTypeColor,
    getRepoTypeLabel,
    getNodeName,
    getNode,
    getNodeStatus,
  };
}
