import type { Component, Ref } from "vue";
import {
  CloudIcon,
  ComputerDesktopIcon,
  FolderIcon,
  ServerIcon,
} from "@heroicons/vue/24/outline";
import type { ResourceType, SourceResource } from "@/types/sourceResource";

type Translate = (key: string, params?: Record<string, any>) => string;

export function useSourceResourceFormatting(
  t: Translate,
  selectedResource: Ref<SourceResource | null>,
) {
  function formatDate(dateStr?: string | null): string {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleString();
  }

  function formatBytes(bytes?: number | null): string {
    if (!bytes) return "0 B";
    const units = ["B", "KB", "MB", "GB", "TB", "PB"];
    let value = bytes;
    let unit = 0;
    while (value >= 1024 && unit < units.length - 1) {
      value /= 1024;
      unit += 1;
    }
    return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[unit]}`;
  }

  function getSourceConnection(resource: SourceResource): string {
    const config = resource.config || {};
    if (resource.resource_type === "local") {
      return config.root_path || config.path || "-";
    }
    if (resource.resource_type === "s3") {
      return config.bucket || "-";
    }
    if (["nas", "nfs", "cifs"].includes(resource.resource_type)) {
      const server = config.server || "";
      const path = config.export_path || config.share || "";
      if (server && path) return `${server}:${path}`;
      return server || path || "-";
    }
    return config.path || config.endpoint || "-";
  }

  function getUsagePercent(resource: SourceResource): number {
    if (
      typeof resource.usage_percentage === "number" &&
      resource.usage_percentage > 0
    ) {
      return Math.min(100, Math.max(0, resource.usage_percentage));
    }
    if (!resource.total_size) return 0;
    return Math.min(
      100,
      Math.max(0, (resource.used_size / resource.total_size) * 100),
    );
  }

  function getCapacityText(resource: SourceResource): string {
    if (!resource.total_size) return "-";
    return `${formatBytes(resource.used_size)} / ${formatBytes(resource.total_size)}`;
  }

  function maskValue(value?: string) {
    if (!value) return "-";
    if (value.length <= 8) return "****";
    return `${value.slice(0, 4)}****${value.slice(-4)}`;
  }

  function getResourceIcon(type: ResourceType): Component {
    switch (type) {
      case "nas":
        return ServerIcon;
      case "nfs":
      case "cifs":
        return FolderIcon;
      case "s3":
      case "azure":
      case "gcs":
        return CloudIcon;
      case "local":
        return ComputerDesktopIcon;
      default:
        return FolderIcon;
    }
  }

  const selectedResourceConfigRows = () => {
    const resource = selectedResource.value;
    if (!resource) return [];
    const config = resource.config || {};
    const credentials = resource.credentials || {};
    const rows: Array<{ label: string; value: string }> = [];

    if (resource.resource_type === "local") {
      rows.push({
        label: t("sourceResources.form.path"),
        value: config.root_path || config.path || "-",
      });
    } else if (["nas", "nfs", "cifs"].includes(resource.resource_type)) {
      rows.push(
        {
          label: t("sourceResources.form.server"),
          value: config.server || "-",
        },
        {
          label:
            resource.resource_type === "cifs"
              ? t("sourceResources.form.share")
              : t("sourceResources.form.exportPath"),
          value: config.share || config.export_path || "-",
        },
        {
          label: t("sourceResources.form.mountOptions"),
          value: config.mount_options || "-",
        },
        {
          label: t("sourceResources.form.username"),
          value: credentials.username || "-",
        },
      );
    } else if (resource.resource_type === "s3") {
      rows.push(
        {
          label: t("sourceResources.form.endpoint"),
          value: config.endpoint || "-",
        },
        {
          label: t("sourceResources.form.bucket"),
          value: config.bucket || "-",
        },
        {
          label: t("sourceResources.form.region"),
          value: config.region || "-",
        },
        {
          label: t("sourceResources.form.prefix"),
          value: config.prefix || "-",
        },
        {
          label: t("sourceResources.form.accessKey"),
          value: maskValue(credentials.access_key),
        },
      );
    }

    return rows;
  };

  const selectedResourceStatsRows = () => {
    const resource = selectedResource.value;
    if (!resource) return [];
    return [
      {
        label: t("sourceResources.connection"),
        value: getSourceConnection(resource),
      },
      {
        label: t("sourceResources.details.totalSize"),
        value: formatBytes(resource.total_size),
      },
      {
        label: t("sourceResources.details.usedSize"),
        value: formatBytes(resource.used_size),
      },
      {
        label: t("sourceResources.details.freeSize"),
        value: formatBytes(resource.free_size),
      },
      {
        label: t("sourceResources.details.usage"),
        value: resource.total_size
          ? `${getUsagePercent(resource).toFixed(1)}%`
          : "-",
      },
      {
        label: t("sourceResources.details.fileCount"),
        value: String(resource.file_count ?? 0),
      },
      {
        label: t("sourceResources.lastConnectionTest"),
        value: formatDate(resource.last_connection_test),
      },
      {
        label: t("common.createdAt"),
        value: formatDate(resource.created_at),
      },
      {
        label: t("common.updatedAt"),
        value: formatDate(resource.updated_at),
      },
    ];
  };

  return {
    formatDate,
    formatBytes,
    getSourceConnection,
    getUsagePercent,
    getCapacityText,
    getResourceIcon,
    selectedResourceConfigRows,
    selectedResourceStatsRows,
  };
}
