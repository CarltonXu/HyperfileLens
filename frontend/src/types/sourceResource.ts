/**
 * Source Resource Types
 *
 * Source Resources represent backup data sources:
 * - NAS/NFS/CIFS network storage
 * - Object Storage (S3, Azure, GCS)
 * - Local Filesystem (Node-direct mode)
 */

export type ResourceType =
  | "nas"
  | "nfs"
  | "cifs"
  | "s3"
  | "azure"
  | "gcs"
  | "local";
export type MountStatus = "mounted" | "unmounted" | "mounting" | "error";
export type ConnectionStatus =
  | "active"
  | "inactive"
  | "connected"
  | "disconnected"
  | "error"
  | "unknown";

export interface SourceResource {
  id: string;
  name: string;
  description: string;
  resource_type: ResourceType;
  resource_type_display: string;

  // Connection configuration
  config: {
    // NFS
    server?: string;
    export_path?: string;
    mount_options?: string;

    // CIFS
    share?: string;
    domain?: string;

    // S3/Azure/GCS
    endpoint?: string;
    bucket?: string;
    prefix?: string;
    region?: string;
    url_style?: "virtual" | "path";
    use_tls?: boolean;

    // Local (empty config)
    root_path?: string;
    path?: string;
  };

  // Credentials (encrypted, only returned when needed)
  credentials?: {
    username?: string;
    password?: string;
    access_key?: string;
    secret_key?: string;
    domain?: string;
  };

  // Bound node for operations
  bound_node: {
    id: string;
    name: string;
    hostname: string;
    status: string;
  } | null;

  // Mount status
  mount_status: MountStatus;
  mount_status_display?: string;
  mount_point: string; // Path on the node where the resource is mounted
  mount_error: string;

  // Status
  status: ConnectionStatus;
  status_display?: string;
  status_message: string;
  last_connection_test: string | null;

  // Statistics
  total_size: number;
  used_size: number;
  free_size?: number;
  usage_percentage?: number;
  file_count: number;

  // Timestamps
  created_at: string;
  updated_at: string;
}

export interface SourceResourceCreateRequest {
  name: string;
  description?: string;
  resource_type: ResourceType;
  config: Record<string, any>;
  credentials?: Record<string, any>;
  bound_node_id?: string | null;
}

export interface SourceResourceUpdateRequest {
  name?: string;
  description?: string;
  config?: Record<string, any>;
  credentials?: Record<string, any>;
  bound_node_id?: string | null;
}

export interface SourceResourceStats {
  total_resources: number;
  active_resources: number;
  mounted_resources: number;
  error_resources: number;
  by_type: {
    nas: number;
    nfs: number;
    cifs: number;
    s3: number;
    azure: number;
    gcs: number;
    local: number;
  };
  total_size: number;
  used_size: number;
}

// Resource type labels
export const RESOURCE_TYPE_LABELS: Record<
  ResourceType,
  { en: string; zh: string }
> = {
  nas: { en: "NAS Storage", zh: "NAS 存储" },
  nfs: { en: "NFS Share", zh: "NFS 共享" },
  cifs: { en: "CIFS/SMB Share", zh: "CIFS/SMB 共享" },
  s3: { en: "Amazon S3", zh: "Amazon S3" },
  azure: { en: "Azure Blob", zh: "Azure Blob" },
  gcs: { en: "Google Cloud Storage", zh: "Google Cloud Storage" },
  local: { en: "Local Filesystem", zh: "本地文件系统" },
};

// Resource type icons
export const RESOURCE_TYPE_ICONS: Record<ResourceType, string> = {
  nas: "server",
  nfs: "folder",
  cifs: "folder",
  s3: "cloud",
  azure: "cloud",
  gcs: "cloud",
  local: "computer",
};
