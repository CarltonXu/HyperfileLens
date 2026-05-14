<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import {
  ArrowPathIcon,
  CheckCircleIcon,
  ChevronRightIcon,
  CloudIcon,
  ComputerDesktopIcon,
  ExclamationCircleIcon,
  FolderIcon,
  ServerIcon,
  SignalIcon,
  XMarkIcon,
  XCircleIcon,
} from "@heroicons/vue/24/outline";
import { nodesApi, sourceResourcesApi } from "@/api";
import type { ResourceType, SourceResource } from "@/types/sourceResource";
import type { ProxyNode } from "@/types/proxy";

const props = defineProps<{
  nodes: ProxyNode[];
  modelValue?: SourceResource | null;
}>();

const emit = defineEmits<{
  close: [];
  save: [Record<string, any>];
}>();

const { t } = useI18n();
const step = ref(1);
const testResult = ref<null | {
  success: boolean;
  message: string;
  details?: any;
  taskId?: string;
}>(null);
const testing = ref(false);
const loadingDirectories = ref(false);
const currentPath = ref("/");
const directories = ref<Array<{ name: string; path: string }>>([]);

const form = reactive({
  name: "",
  description: "",
  source_kind: "local" as "local" | "nas" | "s3",
  nas_protocol: "nfs" as "nfs" | "cifs",
  bound_node: "" as string,
  root_path: "/",
  server: "",
  export_path: "",
  share: "",
  mount_options: "",
  endpoint: "",
  bucket: "",
  prefix: "",
  region: "",
  url_style: "virtual" as "virtual" | "path",
  use_tls: true,
  username: "",
  password: "",
  access_key: "",
  secret_key: "",
});

const sourceTypes = computed(() => [
  {
    value: "local",
    label: t("sourceResources.types.local"),
    description: t("sourceResources.typeDescriptions.local"),
    icon: ComputerDesktopIcon,
  },
  {
    value: "nas",
    label: t("sourceResources.types.nas"),
    description: t("sourceResources.typeDescriptions.nas"),
    icon: ServerIcon,
  },
  {
    value: "s3",
    label: t("sourceResources.types.s3"),
    description: t("sourceResources.typeDescriptions.s3"),
    icon: CloudIcon,
  },
]);

const recommendedNodes = computed(() => {
  if (form.source_kind === "local") {
    return props.nodes.filter(
      (node) => node.role === "agent" || node.role === "sync",
    );
  }
  return props.nodes.filter((node) => node.role === "sync");
});

const canNext = computed(() => {
  if (step.value === 1) return !!form.source_kind;
  if (step.value === 2)
    return !!form.name.trim() && !!form.bound_node && hasConnectionConfig.value;
  if (step.value === 3) return testResult.value?.success === true;
  return true;
});

const hasConnectionConfig = computed(() => {
  if (form.source_kind === "local") return !!form.root_path.trim();
  if (form.source_kind === "nas") {
    if (form.nas_protocol === "nfs")
      return !!form.server.trim() && !!form.export_path.trim();
    return (
      !!form.server.trim() &&
      !!form.share.trim() &&
      !!form.username.trim() &&
      !!form.password.trim()
    );
  }
  return (
    !!form.endpoint.trim() &&
    !!form.bucket.trim() &&
    !!form.access_key.trim() &&
    !!form.secret_key.trim()
  );
});

const endpointPreview = computed(() => {
  if (form.source_kind === "local") return form.root_path || "/";
  if (form.source_kind === "nas") {
    return form.nas_protocol === "nfs"
      ? `${form.server || "-"}:${form.export_path || "-"}`
      : `//${form.server || "-"}/${form.share || "-"}`;
  }
  return `${form.endpoint || "-"}/${form.bucket || ""}${form.prefix ? `/${form.prefix}` : ""}`;
});

const testDetailRows = computed(() => {
  const result = testResult.value;
  const details = result?.details || {};
  const spaceInfo = details.space_info || {};
  const rows: Array<{ label: string; value: string }> = [];

  if (result?.taskId) {
    rows.push({
      label: t("sourceResources.testResult.taskId"),
      value: result.taskId,
    });
  }
  if (details.storage_type) {
    rows.push({
      label: t("sourceResources.testResult.storageType"),
      value: details.storage_type,
    });
  }
  if (details.repository_id) {
    rows.push({
      label: t("sourceResources.testResult.repositoryId"),
      value: details.repository_id,
    });
  }
  if (typeof details.success === "boolean") {
    rows.push({
      label: t("sourceResources.testResult.proxyResult"),
      value: details.success ? t("common.success") : t("common.error"),
    });
  }
  if (typeof spaceInfo.total_bytes === "number") {
    rows.push({
      label: t("sourceResources.testResult.totalSpace"),
      value: formatBytes(spaceInfo.total_bytes),
    });
  }
  if (typeof spaceInfo.used_bytes === "number") {
    rows.push({
      label: t("sourceResources.testResult.usedSpace"),
      value: formatBytes(spaceInfo.used_bytes),
    });
  }
  if (typeof spaceInfo.free_bytes === "number") {
    rows.push({
      label: t("sourceResources.testResult.freeSpace"),
      value: formatBytes(spaceInfo.free_bytes),
    });
  }

  return rows;
});

watch(
  () => props.modelValue,
  (resource) => {
    step.value = resource ? 2 : 1;
    testResult.value = null;
    if (!resource) {
      reset();
      return;
    }
    form.name = resource.name || "";
    form.description = resource.description || "";
    form.bound_node = String(
      (resource.bound_node as any)?.id || resource.bound_node || "",
    );
    form.source_kind =
      resource.resource_type === "s3"
        ? "s3"
        : resource.resource_type === "local"
          ? "local"
          : "nas";
    form.nas_protocol = resource.resource_type === "cifs" ? "cifs" : "nfs";
    const config = resource.config as Record<string, any>;
    form.root_path = config?.root_path || config?.path || "/";
    form.server = resource.config?.server || "";
    form.export_path = resource.config?.export_path || "";
    form.share = resource.config?.share || "";
    form.mount_options = resource.config?.mount_options || "";
    form.endpoint = resource.config?.endpoint || "";
    form.bucket = resource.config?.bucket || "";
    form.prefix = resource.config?.prefix || "";
    form.region = resource.config?.region || "";
    form.url_style = resource.config?.url_style || "virtual";
    form.use_tls = resource.config?.use_tls !== false;
    form.username = resource.credentials?.username || "";
    form.password = "";
    form.access_key = resource.credentials?.access_key || "";
    form.secret_key = "";
  },
  { immediate: true },
);

watch([() => form.bound_node, () => form.source_kind], () => {
  if (form.bound_node && form.source_kind === "local") {
    fetchLocalDirectories(form.root_path || "/");
  }
});

watch(
  [
    () => form.name,
    () => form.bound_node,
    () => form.root_path,
    () => form.server,
    () => form.export_path,
    () => form.share,
    () => form.mount_options,
    () => form.endpoint,
    () => form.bucket,
    () => form.prefix,
    () => form.region,
    () => form.url_style,
    () => form.use_tls,
    () => form.username,
    () => form.password,
    () => form.access_key,
    () => form.secret_key,
  ],
  () => {
    testResult.value = null;
  },
);

const canGoToStep = (targetStep: number) => {
  if (targetStep > step.value + 1) return false;
  if (targetStep > step.value && !canNext.value) return false;
  return true;
};

function reset() {
  Object.assign(form, {
    name: "",
    description: "",
    source_kind: "local",
    nas_protocol: "nfs",
    bound_node: "",
    root_path: "/",
    server: "",
    export_path: "",
    share: "",
    mount_options: "",
    endpoint: "",
    bucket: "",
    prefix: "",
    region: "",
    url_style: "virtual",
    use_tls: true,
    username: "",
    password: "",
    access_key: "",
    secret_key: "",
  });
}

function selectType(type: "local" | "nas" | "s3") {
  if (props.modelValue) return;
  form.source_kind = type;
  testResult.value = null;
  directories.value = [];
  currentPath.value = form.root_path || "/";
}

async function runDraftCheck() {
  testing.value = true;
  testResult.value = null;
  try {
    const response = await sourceResourcesApi.testDraft(buildPayload());
    testResult.value = {
      success: response.data.success,
      message:
        response.data.message || t("sourceResources.wizard.draftCheckPassed"),
      details: response.data.details,
      taskId: response.data.task_id,
    };
  } catch (error: any) {
    testResult.value = {
      success: false,
      message:
        error.response?.data?.message ||
        error.response?.data?.error ||
        t("sourceResources.wizard.draftCheckFailed"),
      details: error.response?.data?.details,
      taskId: error.response?.data?.task_id,
    };
  } finally {
    testing.value = false;
  }
}

async function fetchLocalDirectories(path = form.root_path || "/") {
  if (form.source_kind !== "local" || !form.bound_node) return;
  loadingDirectories.value = true;
  try {
    const response = await nodesApi.getDirectories(
      form.bound_node,
      path || "/",
    );
    currentPath.value = response.data.path || path || "/";
    directories.value =
      response.data.entries ||
      (response.data.directories || []).map((name: string) => ({
        name,
        path:
          currentPath.value === "/"
            ? `/${name}`
            : `${currentPath.value}/${name}`,
      }));
  } catch {
    directories.value = [];
  } finally {
    loadingDirectories.value = false;
  }
}

function navigateLocalDirectory(path: string) {
  form.root_path = path;
  fetchLocalDirectories(path);
}

function navigateUp() {
  if (!currentPath.value || currentPath.value === "/") return;
  const parts = currentPath.value.split("/").filter(Boolean);
  parts.pop();
  navigateLocalDirectory(parts.length ? `/${parts.join("/")}` : "/");
}

function buildPayload() {
  let resource_type: ResourceType = "local";
  const config: Record<string, any> = {};
  const credentials: Record<string, any> = {};

  if (form.source_kind === "local") {
    resource_type = "local";
    config.root_path = form.root_path || "/";
  } else if (form.source_kind === "nas") {
    resource_type = form.nas_protocol;
    config.server = form.server;
    config.mount_options = form.mount_options;
    if (form.nas_protocol === "nfs") config.export_path = form.export_path;
    else {
      config.share = form.share;
      if (form.username) credentials.username = form.username;
      if (form.password) credentials.password = form.password;
    }
  } else {
    resource_type = "s3";
    config.endpoint = form.endpoint;
    config.bucket = form.bucket;
    config.prefix = form.prefix;
    config.region = form.region;
    config.url_style = form.url_style;
    config.use_tls = form.use_tls;
    if (form.access_key) credentials.access_key = form.access_key;
    if (form.secret_key) credentials.secret_key = form.secret_key;
  }

  const payload: Record<string, any> = {
    name: form.name.trim(),
    description: form.description,
    resource_type,
    config,
    bound_node: form.bound_node || null,
  };
  const spaceInfo = testResult.value?.details?.space_info;
  if (testResult.value?.success && spaceInfo) {
    payload.total_size = spaceInfo.total_bytes || 0;
    payload.used_size = spaceInfo.used_bytes || 0;
    payload.free_size = spaceInfo.free_bytes || 0;
    payload.file_count = testResult.value.details?.object_count || 0;
  }
  if (Object.keys(credentials).length > 0) {
    payload.credentials = credentials;
  }
  return payload;
}

function formatBytes(bytes?: number): string {
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

function save() {
  emit("save", buildPayload());
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/50" @click="emit('close')" />
      <div
        class="relative modal-surface rounded-2xl shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col"
      >
        <div
          class="px-6 py-4 border-b border-border flex items-center justify-between flex-shrink-0"
        >
          <div>
            <h2 class="text-lg font-semibold text-foreground">
              {{
                modelValue
                  ? t("sourceResources.editResource")
                  : t("sourceResources.addResource")
              }}
            </h2>
            <p class="mt-1 text-sm text-foreground-secondary">
              {{ t("sourceResources.wizard.subtitle") }}
            </p>
          </div>
          <button
            class="p-1 hover:bg-background-tertiary/50 rounded-lg"
            @click="emit('close')"
          >
            <XMarkIcon class="w-5 h-5 text-foreground-muted" />
          </button>
        </div>

        <div
          class="px-6 py-3 border-b border-border bg-background/30 flex-shrink-0"
        >
          <div class="grid grid-cols-4 gap-2">
            <button
              v-for="item in [
                { value: 1, label: t('sourceResources.wizard.type') },
                { value: 2, label: t('sourceResources.wizard.connection') },
                { value: 3, label: t('sourceResources.wizard.test') },
                { value: 4, label: t('sourceResources.wizard.review') },
              ]"
              :key="item.value"
              type="button"
              :class="[
                'flex items-center justify-center gap-2 rounded-lg px-2 py-2 text-xs font-medium transition-colors',
                !canGoToStep(item.value)
                  ? 'opacity-50 cursor-not-allowed'
                  : step === item.value
                    ? 'bg-blue-600 text-white'
                    : step > item.value
                      ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300'
                      : 'text-foreground-secondary hover:bg-hover',
              ]"
              @click="canGoToStep(item.value) && (step = item.value)"
            >
              <span
                :class="[
                  'flex h-5 w-5 items-center justify-center rounded-full text-[11px]',
                  step === item.value
                    ? 'bg-white/20'
                    : step > item.value
                      ? 'bg-emerald-100 dark:bg-emerald-900/40'
                      : 'bg-background-secondary',
                ]"
              >
                {{ item.value }}
              </span>
              <span class="truncate">{{ item.label }}</span>
            </button>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto p-6 space-y-4">
          <div v-if="step === 1" class="space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
              <button
                v-for="type in sourceTypes"
                :key="type.value"
                type="button"
                :disabled="!!modelValue"
                :class="[
                  'text-left rounded-xl border-2 p-4 transition-all',
                  modelValue ? 'cursor-not-allowed opacity-60' : '',
                  form.source_kind === type.value
                    ? 'border-blue-500 dark:border-blue-400 bg-background/50 shadow-sm'
                    : 'border-border bg-background/50 hover:border-border-secondary',
                ]"
                @click="!modelValue && selectType(type.value as any)"
              >
                <div class="flex items-center gap-3">
                  <div
                    class="w-10 h-10 rounded-lg bg-background-secondary flex items-center justify-center text-blue-600 dark:text-blue-400"
                  >
                    <component :is="type.icon" class="w-5 h-5" />
                  </div>
                  <div class="min-w-0">
                    <p class="font-semibold text-sm text-foreground">
                      {{ type.label }}
                    </p>
                    <p class="text-xs text-foreground-secondary mt-1 leading-5">
                      {{ type.description }}
                    </p>
                  </div>
                </div>
              </button>
            </div>
          </div>

          <div v-else-if="step === 2" class="space-y-4">
            <div
              class="space-y-4 p-4 rounded-xl border border-border bg-background/30"
            >
              <h3 class="text-sm font-semibold text-foreground">
                {{ t("sourceResources.wizard.basicInfo") }}
              </h3>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label class="block text-sm font-medium text-foreground mb-1"
                    >{{ t("sourceResources.form.name") }} *</label
                  >
                  <input
                    v-model="form.name"
                    :placeholder="t('common.name')"
                    class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label class="block text-sm font-medium text-foreground mb-1"
                    >{{ t("sourceResources.form.boundNode") }} *</label
                  >
                  <select
                    v-model="form.bound_node"
                    class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">
                      {{ t("sourceResources.form.selectNode") }}
                    </option>
                    <option
                      v-for="node in recommendedNodes"
                      :key="node.id"
                      :value="node.id"
                    >
                      {{ node.name }} ({{ node.role }})
                    </option>
                  </select>
                </div>
              </div>
              <div>
                <label class="block text-sm font-medium text-foreground mb-1">{{
                  t("common.description")
                }}</label>
                <input
                  v-model="form.description"
                  :placeholder="t('common.description')"
                  class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div
              v-if="form.source_kind === 'local'"
              class="space-y-4 p-4 rounded-xl border border-border bg-background/30"
            >
              <h3 class="text-sm font-semibold text-foreground">
                {{ t("sourceResources.wizard.localPathConfig") }}
              </h3>
              <div
                class="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-3 items-end"
              >
                <div>
                  <label class="block text-sm font-medium text-foreground mb-1"
                    >{{ t("sourceResources.form.path") }} *</label
                  >
                  <input
                    v-model="form.root_path"
                    placeholder="/"
                    class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <button
                  type="button"
                  class="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg border border-border text-sm text-foreground hover:bg-hover disabled:opacity-50"
                  :disabled="!form.bound_node || loadingDirectories"
                  @click="fetchLocalDirectories(form.root_path || '/')"
                >
                  <FolderIcon class="w-4 h-4" />
                  {{
                    loadingDirectories
                      ? t("common.loading")
                      : t("sourceResources.wizard.browsePath")
                  }}
                </button>
              </div>
              <div
                class="rounded-lg border border-border bg-background/50 overflow-hidden"
              >
                <div
                  class="px-3 py-2 border-b border-border flex items-center justify-between bg-background-secondary/60"
                >
                  <code class="text-xs text-foreground break-all">{{
                    currentPath || "/"
                  }}</code>
                  <button
                    type="button"
                    class="text-xs text-blue-600 dark:text-blue-400 hover:underline disabled:text-foreground-muted"
                    :disabled="currentPath === '/'"
                    @click="navigateUp"
                  >
                    {{ t("repository.local.goUp") }}
                  </button>
                </div>
                <div class="max-h-48 overflow-y-auto">
                  <div
                    v-if="loadingDirectories"
                    class="py-8 text-center text-sm text-foreground-secondary"
                  >
                    {{ t("common.loading") }}
                  </div>
                  <div
                    v-else-if="directories.length === 0"
                    class="py-8 text-center text-sm text-foreground-secondary"
                  >
                    {{ t("repository.local.noSubdirectories") }}
                  </div>
                  <button
                    v-for="dir in directories"
                    :key="dir.path"
                    type="button"
                    class="w-full px-3 py-2 flex items-center gap-2 text-left text-sm hover:bg-hover border-b border-border last:border-b-0"
                    @click="navigateLocalDirectory(dir.path)"
                  >
                    <FolderIcon class="w-4 h-4 text-blue-500" />
                    <span class="text-foreground font-medium">{{
                      dir.name
                    }}</span>
                    <ChevronRightIcon
                      class="w-4 h-4 text-foreground-muted ml-auto"
                    />
                  </button>
                </div>
              </div>
            </div>

            <div
              v-if="form.source_kind === 'nas'"
              class="space-y-4 p-4 rounded-xl border border-border bg-background/30"
            >
              <h3 class="text-sm font-semibold text-foreground">
                {{ t("sourceResources.wizard.nasConfig") }}
              </h3>
              <div class="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  :class="[
                    'px-4 py-2 rounded-lg text-sm font-medium border transition-colors',
                    form.nas_protocol === 'nfs'
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'border-border text-foreground-secondary hover:bg-hover',
                  ]"
                  @click="form.nas_protocol = 'nfs'"
                >
                  NFS
                </button>
                <button
                  type="button"
                  :class="[
                    'px-4 py-2 rounded-lg text-sm font-medium border transition-colors',
                    form.nas_protocol === 'cifs'
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'border-border text-foreground-secondary hover:bg-hover',
                  ]"
                  @click="form.nas_protocol = 'cifs'"
                >
                  SMB/CIFS
                </button>
              </div>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label class="block text-sm font-medium text-foreground mb-1"
                    >{{ t("sourceResources.form.server") }} *</label
                  >
                  <input
                    v-model="form.server"
                    placeholder="192.168.1.100"
                    class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div v-if="form.nas_protocol === 'nfs'">
                  <label class="block text-sm font-medium text-foreground mb-1"
                    >{{ t("sourceResources.form.exportPath") }} *</label
                  >
                  <input
                    v-model="form.export_path"
                    placeholder="/export/data"
                    class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div v-else>
                  <label class="block text-sm font-medium text-foreground mb-1"
                    >{{ t("sourceResources.form.share") }} *</label
                  >
                  <input
                    v-model="form.share"
                    placeholder="shared-folder"
                    class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div class="md:col-span-2">
                  <label
                    class="block text-sm font-medium text-foreground mb-1"
                    >{{ t("sourceResources.form.mountOptions") }}</label
                  >
                  <input
                    v-model="form.mount_options"
                    placeholder="rw,vers=4"
                    class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <template v-if="form.nas_protocol === 'cifs'">
                  <div>
                    <label
                      class="block text-sm font-medium text-foreground mb-1"
                      >{{ t("sourceResources.form.username") }} *</label
                    >
                    <input
                      v-model="form.username"
                      placeholder="admin"
                      class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label
                      class="block text-sm font-medium text-foreground mb-1"
                      >{{ t("sourceResources.form.password") }} *</label
                    >
                    <input
                      v-model="form.password"
                      type="password"
                      class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </template>
              </div>
            </div>

            <div
              v-if="form.source_kind === 's3'"
              class="space-y-4 p-4 rounded-xl border border-border bg-background/30"
            >
              <h3 class="text-sm font-semibold text-foreground">
                {{ t("sourceResources.wizard.s3Config") }}
              </h3>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label class="block text-sm font-medium text-foreground mb-1"
                    >{{ t("sourceResources.form.endpoint") }} *</label
                  >
                  <input
                    v-model="form.endpoint"
                    placeholder="https://s3.amazonaws.com"
                    class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p class="mt-1 text-xs text-foreground-secondary">
                    {{ t("sourceResources.form.endpointHint") }}
                  </p>
                </div>
                <div>
                  <label class="block text-sm font-medium text-foreground mb-1"
                    >{{ t("sourceResources.form.bucket") }} *</label
                  >
                  <input
                    v-model="form.bucket"
                    placeholder="my-backup-bucket"
                    class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p class="mt-1 text-xs text-foreground-secondary">
                    {{ t("sourceResources.form.bucketHint") }}
                  </p>
                </div>
                <div>
                  <label
                    class="block text-sm font-medium text-foreground mb-1"
                    >{{ t("sourceResources.form.region") }}</label
                  >
                  <input
                    v-model="form.region"
                    placeholder="us-east-1"
                    class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p class="mt-1 text-xs text-foreground-secondary">
                    {{ t("sourceResources.form.regionHint") }}
                  </p>
                </div>
                <div>
                  <label
                    class="block text-sm font-medium text-foreground mb-1"
                    >{{ t("sourceResources.form.urlStyle") }}</label
                  >
                  <select
                    v-model="form.url_style"
                    class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option class="bg-background" value="virtual">
                      {{ t("sourceResources.form.urlStyleVirtual") }}
                    </option>
                    <option class="bg-background" value="path">
                      {{ t("sourceResources.form.urlStylePath") }}
                    </option>
                  </select>
                  <p class="mt-1 text-xs text-foreground-secondary">
                    {{ t("sourceResources.form.urlStyleHint") }}
                  </p>
                </div>
                <div
                  class="rounded-lg border border-border bg-background/40 px-3 py-2"
                >
                  <div class="flex items-center justify-between gap-3">
                    <div>
                      <p class="text-sm font-medium text-foreground">
                        {{ t("sourceResources.form.useTLS") }}
                      </p>
                      <p class="mt-1 text-xs text-foreground-secondary">
                        {{ t("sourceResources.form.useTLSHint") }}
                      </p>
                    </div>
                    <button
                      type="button"
                      role="switch"
                      :aria-checked="form.use_tls"
                      @click="form.use_tls = !form.use_tls"
                      :class="[
                        'relative inline-flex h-6 w-11 shrink-0 rounded-full transition-colors',
                        form.use_tls ? 'bg-blue-600' : 'bg-background-tertiary',
                      ]"
                    >
                      <span
                        :class="[
                          'inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform mt-0.5',
                          form.use_tls ? 'translate-x-5' : 'translate-x-0.5',
                        ]"
                      />
                    </button>
                  </div>
                </div>
                <div>
                  <label
                    class="block text-sm font-medium text-foreground mb-1"
                    >{{ t("sourceResources.form.prefix") }}</label
                  >
                  <input
                    v-model="form.prefix"
                    placeholder="backups/"
                    class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p class="mt-1 text-xs text-foreground-secondary">
                    {{ t("sourceResources.form.prefixHint") }}
                  </p>
                </div>
                <div>
                  <label class="block text-sm font-medium text-foreground mb-1"
                    >{{ t("sourceResources.form.accessKey") }} *</label
                  >
                  <input
                    v-model="form.access_key"
                    placeholder="AKIAIOSFODNN7EXAMPLE"
                    class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p class="mt-1 text-xs text-foreground-secondary">
                    {{ t("sourceResources.form.accessKeyHint") }}
                  </p>
                </div>
                <div>
                  <label class="block text-sm font-medium text-foreground mb-1"
                    >{{ t("sourceResources.form.secretKey") }} *</label
                  >
                  <input
                    v-model="form.secret_key"
                    type="password"
                    class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p class="mt-1 text-xs text-foreground-secondary">
                    {{ t("sourceResources.form.secretKeyHint") }}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div
            v-else-if="step === 3"
            class="space-y-4 p-4 rounded-xl border border-border bg-background/30"
          >
            <div class="flex items-start gap-3">
              <div
                class="flex items-center justify-center w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
              >
                <ExclamationCircleIcon class="w-5 h-5" />
              </div>
              <div class="flex-1">
                <p class="font-semibold text-sm text-foreground">
                  {{ t("sourceResources.wizard.testTitle") }}
                </p>
                <p class="text-sm text-foreground-secondary mt-1">
                  {{ t("sourceResources.wizard.testDescription") }}
                </p>
                <button
                  type="button"
                  class="mt-4 inline-flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  :disabled="
                    testing || !hasConnectionConfig || !form.bound_node
                  "
                  :title="
                    testing
                      ? t('common.loading')
                      : t('sourceResources.testConnection')
                  "
                  :aria-label="
                    testing
                      ? t('common.loading')
                      : t('sourceResources.testConnection')
                  "
                  @click="runDraftCheck"
                >
                  <ArrowPathIcon v-if="testing" class="h-4 w-4 animate-spin" />
                  <SignalIcon v-else class="h-4 w-4" />
                </button>
                <div
                  v-if="testResult"
                  class="mt-4 p-4 rounded-xl border border-border bg-background/50"
                >
                  <div class="flex items-start gap-3">
                    <CheckCircleIcon
                      v-if="testResult.success"
                      class="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0"
                    />
                    <XCircleIcon
                      v-else
                      class="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0"
                    />
                    <div>
                      <p
                        :class="[
                          'font-semibold',
                          testResult.success
                            ? 'text-foreground'
                            : 'text-red-700 dark:text-red-400',
                        ]"
                      >
                        {{
                          testResult.success
                            ? t("common.success")
                            : t("common.error")
                        }}
                      </p>
                      <p
                        :class="[
                          'text-sm mt-1',
                          testResult.success
                            ? 'text-foreground-secondary'
                            : 'text-red-600 dark:text-red-300',
                        ]"
                      >
                        {{ testResult.message }}
                      </p>
                      <dl
                        v-if="testDetailRows.length"
                        class="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2"
                      >
                        <div
                          v-for="row in testDetailRows"
                          :key="row.label"
                          class="rounded-lg border border-border bg-background-secondary/50 px-3 py-2"
                        >
                          <dt class="text-xs text-foreground-secondary">
                            {{ row.label }}
                          </dt>
                          <dd
                            class="mt-1 text-sm font-medium text-foreground break-all"
                          >
                            {{ row.value || "-" }}
                          </dd>
                        </div>
                      </dl>
                      <details v-if="testResult.details" class="mt-3 text-xs">
                        <summary class="cursor-pointer font-medium">
                          {{ t("sourceResources.testResult.rawDetails") }}
                        </summary>
                        <pre
                          class="mt-2 max-h-40 overflow-auto rounded-lg border border-border bg-background-secondary/50 p-3 whitespace-pre-wrap break-all text-foreground"
                          >{{
                            JSON.stringify(testResult.details, null, 2)
                          }}</pre
                        >
                      </details>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div
            v-else
            class="space-y-4 p-4 rounded-xl border border-border bg-background/30"
          >
            <h3 class="text-sm font-semibold text-foreground">
              {{ t("sourceResources.wizard.configSummary") }}
            </h3>
            <dl class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
              <div class="rounded-lg border border-border bg-background/50 p-3">
                <dt class="text-foreground-secondary mb-1">
                  {{ t("sourceResources.form.name") }}
                </dt>
                <dd class="text-foreground font-medium">
                  {{ form.name || "-" }}
                </dd>
              </div>
              <div class="rounded-lg border border-border bg-background/50 p-3">
                <dt class="text-foreground-secondary mb-1">
                  {{ t("sourceResources.form.type") }}
                </dt>
                <dd class="text-foreground font-medium">
                  {{
                    sourceTypes.find((item) => item.value === form.source_kind)
                      ?.label || "-"
                  }}
                </dd>
              </div>
              <div class="rounded-lg border border-border bg-background/50 p-3">
                <dt class="text-foreground-secondary mb-1">
                  {{ t("sourceResources.boundNode") }}
                </dt>
                <dd class="text-foreground font-medium">
                  {{
                    recommendedNodes.find((n) => n.id === form.bound_node)
                      ?.name || "-"
                  }}
                </dd>
              </div>
              <div class="rounded-lg border border-border bg-background/50 p-3">
                <dt class="text-foreground-secondary mb-1">
                  {{ t("sourceResources.form.endpoint") }}
                </dt>
                <dd class="text-foreground font-medium break-all">
                  {{ endpointPreview }}
                </dd>
              </div>
            </dl>
          </div>
        </div>

        <div
          class="px-6 py-4 rounded-2xl border-t border-border bg-card flex justify-between items-center flex-shrink-0"
        >
          <button
            class="px-4 py-2 text-sm font-medium text-foreground-secondary hover:bg-hover rounded-lg disabled:opacity-50"
            :disabled="step === 1"
            @click="step--"
          >
            {{ t("common.back") }}
          </button>
          <div class="flex gap-3">
            <button
              class="px-4 py-2 text-sm font-medium text-foreground-secondary hover:bg-hover rounded-lg"
              @click="emit('close')"
            >
              {{ t("common.cancel") }}
            </button>
            <button
              v-if="step < 4"
              class="px-5 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              :disabled="!canNext"
              @click="step++"
            >
              {{ t("common.next") }}
            </button>
            <button
              v-else
              class="px-5 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              :disabled="!canNext"
              @click="save"
            >
              {{ t("common.save") }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
