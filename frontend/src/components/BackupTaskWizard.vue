<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import {
  ArrowPathIcon,
  CheckCircleIcon,
  CircleStackIcon,
  ClockIcon,
  CloudIcon,
  ComputerDesktopIcon,
  ExclamationCircleIcon,
  FolderIcon,
  MagnifyingGlassIcon,
  ServerIcon,
  ShieldCheckIcon,
  TagIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline";
import { sourceResourcesApi } from "@/api";
import type { BackupTaskCreateData } from "@/types/backup";
import type { Repository } from "@/types/repository";
import type { SourceResource } from "@/types/sourceResource";

const props = defineProps<{
  sources: SourceResource[];
  repositories: Repository[];
  policies: Array<Record<string, any>>;
}>();

const emit = defineEmits<{
  close: [];
  save: [BackupTaskCreateData];
}>();

const { t } = useI18n();

type SourceKind = "local" | "nas" | "s3";
type ScheduleMode = "manual" | "interval" | "cron";
type RetentionMode = "policy" | "custom";

const step = ref(1);
const searchQuery = ref("");
const directoryLoading = ref(false);
const directoryError = ref("");
const currentPath = ref("/");
const directories = ref<Array<{ name: string; path: string }>>([]);
const tagInput = ref("");

const form = reactive({
  name: "",
  description: "",
  tags: [] as string[],
  source_kind: "local" as SourceKind,
  source_resource: "",
  target_repository: "",
  backup_paths: [] as string[],
  exclude_patterns: [] as string[],
  task_type: "incremental" as "full" | "incremental" | "differential",
  priority: "normal" as "low" | "normal" | "high",
  schedule_mode: "manual" as ScheduleMode,
  interval_value: 4,
  interval_unit: "hours" as "minutes" | "hours" | "days",
  cron_expression: "",
  retention_mode: "policy" as RetentionMode,
  schedule: "" as string,
  retention_days: 30,
  max_snapshots: 10,
  compression_enabled: true,
  encryption_enabled: true,
  compression_type: "zstd",
});

const steps = computed(() => [
  t("backupTasks.wizard.basic"),
  t("backupTasks.wizard.source"),
  t("backupTasks.wizard.backupRepository"),
  t("backupTasks.wizard.scheduleRetention"),
  t("backupTasks.wizard.review"),
]);

const localSources = computed(() =>
  props.sources.filter((source) => source.resource_type === "local"),
);

const nasSources = computed(() =>
  props.sources.filter((source) =>
    ["nas", "nfs", "cifs"].includes(source.resource_type),
  ),
);

const s3Sources = computed(() =>
  props.sources.filter((source) => source.resource_type === "s3"),
);

const sourceKinds = computed(() => [
  {
    value: "local" as SourceKind,
    label: t("backupTasks.sourceKinds.local"),
    description: t("backupTasks.sourceKinds.localDesc"),
    icon: ComputerDesktopIcon,
    count: localSources.value.length,
  },
  {
    value: "nas" as SourceKind,
    label: t("backupTasks.sourceKinds.nas"),
    description: t("backupTasks.sourceKinds.nasDesc"),
    icon: ServerIcon,
    count: nasSources.value.length,
  },
  {
    value: "s3" as SourceKind,
    label: t("backupTasks.sourceKinds.s3"),
    description: t("backupTasks.sourceKinds.s3Desc"),
    icon: CloudIcon,
    count: s3Sources.value.length,
  },
]);

const visibleSources = computed(() => {
  if (form.source_kind === "local") return localSources.value;
  if (form.source_kind === "nas") return nasSources.value;
  return s3Sources.value;
});

const filteredSources = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();
  if (!query) return visibleSources.value;
  return visibleSources.value.filter((source) => {
    const node = sourceNodeName(source).toLowerCase();
    return (
      source.name.toLowerCase().includes(query) ||
      source.resource_type.toLowerCase().includes(query) ||
      node.includes(query)
    );
  });
});

const selectedSource = computed(() =>
  props.sources.find((source) => source.id === form.source_resource),
);

const selectedRepository = computed(() =>
  props.repositories.find((repo) => repo.id === form.target_repository),
);

const selectedPolicy = computed(() =>
  props.policies.find((policy) => policy.id === form.schedule),
);

const repositoryDetails = computed(() => {
  const repo = selectedRepository.value;
  if (!repo) return [];
  const config = repo.config || {};
  const credentials = repo.credentials_masked || {};
  const rows: Array<{ label: string; value: string }> = [
    {
      label: t("backupTasks.repositoryDetails.type"),
      value: repo.repo_type_display || repo.repo_type,
    },
    {
      label: t("common.status"),
      value: repo.status_display || repo.status,
    },
  ];

  if (repo.repo_type === "s3") {
    rows.push(
      {
        label: t("backupTasks.repositoryDetails.endpoint"),
        value: config.endpoint || "-",
      },
      {
        label: t("backupTasks.repositoryDetails.bucket"),
        value: config.bucket || "-",
      },
      {
        label: t("backupTasks.repositoryDetails.region"),
        value: config.region || "-",
      },
      {
        label: t("backupTasks.repositoryDetails.prefix"),
        value: config.prefix || "-",
      },
      {
        label: t("backupTasks.repositoryDetails.accessKey"),
        value: credentials.access_key || maskValue(config.access_key),
      },
    );
  } else if (["nas", "nfs", "cifs"].includes(repo.repo_type)) {
    rows.push(
      {
        label: t("backupTasks.repositoryDetails.endpoint"),
        value:
          config.server && config.export_path
            ? `${config.server}:${config.export_path}`
            : config.server || "-",
      },
      {
        label: t("backupTasks.repositoryDetails.mountPoint"),
        value: config.export_path || config.path || "-",
      },
      {
        label: t("backupTasks.repositoryDetails.mountOptions"),
        value: config.mount_options || "-",
      },
      {
        label: t("backupTasks.repositoryDetails.username"),
        value: credentials.username || config.username || "-",
      },
    );
  } else if (repo.repo_type === "local") {
    rows.push(
      {
        label: t("backupTasks.repositoryDetails.path"),
        value: config.path || "-",
      },
      {
        label: t("backupTasks.repositoryDetails.boundNode"),
        value: repo.bound_node_name || "-",
      },
    );
  }

  rows.push(
    {
      label: t("backupTasks.repositoryDetails.kopia"),
      value: repo.kopia_initialized ? t("common.yes") : t("common.no"),
    },
    {
      label: t("backupTasks.repositoryDetails.snapshots"),
      value: String(repo.snapshot_count ?? 0),
    },
  );

  return rows;
});

const includePathsText = computed({
  get: () => form.backup_paths.join("\n"),
  set: (value: string) => {
    form.backup_paths = value
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean);
  },
});

const excludePatternsText = computed({
  get: () => form.exclude_patterns.join("\n"),
  set: (value: string) => {
    form.exclude_patterns = value
      .split(/[\n,]+/)
      .map((item) => item.trim())
      .filter(Boolean);
  },
});

const rootPath = computed(() => {
  const source = selectedSource.value;
  if (!source) return "/";
  if (source.resource_type === "local") {
    return source.config?.root_path || source.config?.path || "/";
  }
  if (source.resource_type === "s3") {
    return source.config?.prefix || "/";
  }
  return source.mount_point || "/";
});

const repositoryCapacity = computed(() => {
  const repo = selectedRepository.value as any;
  const used = repo?.used_bytes || repo?.used_capacity || repo?.size_bytes || 0;
  const total = repo?.quota_bytes || repo?.capacity_bytes || 0;
  if (!total) return t("backupTasks.wizard.capacityUnknown");
  return `${formatBytes(used)} / ${formatBytes(total)}`;
});

const scheduleSummary = computed(() => {
  if (form.schedule_mode === "manual") return t("backupTasks.schedule.manual");
  if (form.schedule_mode === "cron") {
    return form.cron_expression || t("backupTasks.schedule.cron");
  }
  return t("backupTasks.schedule.intervalSummary", {
    value: form.interval_value,
    unit: t(`backupTasks.schedule.units.${form.interval_unit}`),
  });
});

const retentionSummary = computed(() => {
  if (form.retention_mode === "policy") {
    return selectedPolicy.value?.name || t("backupTasks.form.noPolicy");
  }
  return t("backupTasks.retention.customSummary", {
    snapshots: form.max_snapshots,
    days: form.retention_days,
  });
});

const canNext = computed(() => {
  if (step.value === 1) return !!form.name.trim();
  if (step.value === 2) {
    return !!form.source_resource && form.backup_paths.length > 0;
  }
  if (step.value === 3) return !!form.target_repository;
  if (step.value === 4) {
    if (form.schedule_mode === "cron" && !form.cron_expression.trim()) {
      return false;
    }
    if (form.retention_mode === "policy") return !!form.schedule;
    return form.retention_days > 0 && form.max_snapshots > 0;
  }
  return true;
});

watch(
  () => form.source_kind,
  () => {
    form.source_resource = "";
    form.backup_paths = [];
    directories.value = [];
    directoryError.value = "";
    currentPath.value = "/";
  },
);

watch(
  () => form.source_resource,
  () => {
    form.backup_paths = [];
    directories.value = [];
    directoryError.value = "";
    currentPath.value = rootPath.value || "/";
    if (selectedSource.value) {
      void fetchDirectories(currentPath.value);
    }
  },
);

function sourceNodeName(source?: SourceResource) {
  if (!source) return "";
  if (source.bound_node && typeof source.bound_node === "object") {
    return source.bound_node.name;
  }
  return (source as any).bound_node_name || "";
}

function sourceNodeStatus(source?: SourceResource) {
  if (!source) return "";
  if (source.bound_node && typeof source.bound_node === "object") {
    return source.bound_node.status || "";
  }
  return (source as any).bound_node_status || "";
}

function maskValue(value?: string) {
  if (!value) return "-";
  if (value.length <= 8) return "****";
  return `${value.slice(0, 4)}****${value.slice(-4)}`;
}

function addTag() {
  const value = tagInput.value.trim();
  if (!value || form.tags.includes(value)) return;
  form.tags.push(value);
  tagInput.value = "";
}

function removeTag(tag: string) {
  form.tags = form.tags.filter((item) => item !== tag);
}

function selectSource(source: SourceResource) {
  form.source_resource = source.id;
}

function togglePath(path: string) {
  if (form.backup_paths.includes(path)) {
    form.backup_paths = form.backup_paths.filter((item) => item !== path);
  } else {
    form.backup_paths.push(path);
  }
}

async function fetchDirectories(path = rootPath.value || "/") {
  const source = selectedSource.value;
  if (!source || source.resource_type === "s3") {
    directories.value = [];
    return;
  }

  directoryLoading.value = true;
  directoryError.value = "";
  try {
    const response = await sourceResourcesApi.scan(
      source.id,
      path || undefined,
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
  } catch (error: any) {
    directories.value = [];
    directoryError.value =
      error.response?.data?.message ||
      error.response?.data?.error ||
      t("backupTasks.wizard.directoryLoadFailed");
  } finally {
    directoryLoading.value = false;
  }
}

function navigateDirectory(path: string) {
  void fetchDirectories(path);
}

function navigateUp() {
  if (!currentPath.value || currentPath.value === "/") return;
  const normalized = currentPath.value.replace(/[\\/]+$/, "");
  const separator = normalized.includes("\\") ? "\\" : "/";
  const parts = normalized.split(/[\\/]+/).filter(Boolean);
  parts.pop();
  if (separator === "\\" && /^[A-Za-z]:$/.test(parts[0] || "")) {
    void fetchDirectories(
      parts.length === 1 ? `${parts[0]}\\` : parts.join("\\"),
    );
    return;
  }
  void fetchDirectories(parts.length ? `/${parts.join("/")}` : "/");
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
  const schedule =
    form.retention_mode === "policy" && form.schedule ? form.schedule : null;

  emit("save", {
    name: form.name.trim(),
    description: form.description,
    source_resource: form.source_resource,
    target_repository: form.target_repository,
    task_type: form.task_type,
    priority: form.priority,
    backup_paths: [...form.backup_paths],
    exclude_patterns: [...form.exclude_patterns],
    include_patterns: [],
    compression_enabled: form.compression_enabled,
    compression_type: form.compression_type,
    encryption_enabled: form.encryption_enabled,
    schedule,
    retention_days: form.retention_days,
    max_snapshots: form.max_snapshots,
  });
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/50" @click="emit('close')" />
      <div
        class="relative modal-surface rounded-2xl shadow-xl w-full max-w-5xl max-h-[92vh] flex flex-col"
      >
        <div
          class="px-6 py-4 border-b border-border flex items-center justify-between flex-shrink-0"
        >
          <div>
            <h2 class="text-lg font-semibold text-foreground">
              {{ t("backupTasks.createTask") }}
            </h2>
            <p class="mt-1 text-sm text-foreground-secondary">
              {{ t("backupTasks.wizard.subtitle") }}
            </p>
          </div>
          <button class="p-1 rounded-lg hover:bg-hover" @click="emit('close')">
            <XMarkIcon class="w-5 h-5 text-foreground-muted" />
          </button>
        </div>

        <div class="px-6 py-4 border-b border-border flex-shrink-0">
          <div class="flex items-center gap-2 overflow-x-auto">
            <template v-for="(item, index) in steps" :key="item">
              <button
                type="button"
                :class="[
                  'flex items-center gap-2 shrink-0 rounded-lg px-2 py-1.5 transition-colors',
                  step === index + 1
                    ? 'bg-blue-600 text-white'
                    : step > index + 1
                      ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300'
                      : 'text-foreground-secondary hover:bg-hover',
                ]"
                @click="step = index + 1"
              >
                <span
                  :class="[
                    'w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold',
                    step === index + 1
                      ? 'bg-white/20'
                      : step > index + 1
                        ? 'bg-emerald-100 dark:bg-emerald-900/40'
                        : 'bg-background-secondary',
                  ]"
                >
                  {{ index + 1 }}
                </span>
                <span class="text-xs font-medium whitespace-nowrap">
                  {{ item }}
                </span>
              </button>
              <div
                v-if="index < steps.length - 1"
                class="h-px w-8 shrink-0 bg-border"
              />
            </template>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto p-6">
          <div v-if="step === 1" class="space-y-5">
            <div class="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-5">
              <div class="space-y-4">
                <label class="block">
                  <span class="text-sm font-medium text-foreground">
                    {{ t("backupTasks.form.taskName") }} *
                  </span>
                  <input
                    v-model="form.name"
                    class="mt-1 w-full px-3 py-2 rounded-lg border border-border bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                    :placeholder="t('backupTasks.placeholders.taskName')"
                  />
                </label>
                <label class="block">
                  <span class="text-sm font-medium text-foreground">
                    {{ t("common.description") }}
                  </span>
                  <textarea
                    v-model="form.description"
                    rows="4"
                    class="mt-1 w-full px-3 py-2 rounded-lg border border-border bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                    :placeholder="t('backupTasks.placeholders.description')"
                  />
                </label>
                <div>
                  <span class="text-sm font-medium text-foreground">
                    {{ t("backupTasks.form.businessTags") }}
                  </span>
                  <div class="mt-2 flex flex-wrap gap-2">
                    <button
                      v-for="tag in form.tags"
                      :key="tag"
                      type="button"
                      class="inline-flex items-center gap-1 rounded-full border border-border bg-background-secondary px-2.5 py-1 text-xs text-foreground"
                      @click="removeTag(tag)"
                    >
                      <TagIcon class="w-3.5 h-3.5" />
                      {{ tag }}
                      <XMarkIcon class="w-3.5 h-3.5 text-foreground-muted" />
                    </button>
                    <form class="flex gap-2" @submit.prevent="addTag">
                      <input
                        v-model="tagInput"
                        class="w-32 px-3 py-1 rounded-full border border-border bg-background/50 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                        :placeholder="t('backupTasks.placeholders.addTag')"
                      />
                    </form>
                  </div>
                </div>
              </div>
              <div
                class="rounded-xl border border-border bg-background/30 p-4 space-y-3"
              >
                <p class="text-sm font-semibold text-foreground">
                  {{ t("backupTasks.wizard.basicChecklist") }}
                </p>
                <div class="space-y-2 text-sm">
                  <div
                    class="flex items-center gap-2 text-foreground-secondary"
                  >
                    <CheckCircleIcon
                      :class="[
                        'w-5 h-5',
                        form.name.trim()
                          ? 'text-emerald-500'
                          : 'text-foreground-muted',
                      ]"
                    />
                    {{ t("backupTasks.wizard.nameReady") }}
                  </div>
                  <div
                    class="flex items-center gap-2 text-foreground-secondary"
                  >
                    <CheckCircleIcon
                      :class="[
                        'w-5 h-5',
                        form.description.trim()
                          ? 'text-emerald-500'
                          : 'text-foreground-muted',
                      ]"
                    />
                    {{ t("backupTasks.wizard.descriptionReady") }}
                  </div>
                  <div
                    class="flex items-center gap-2 text-foreground-secondary"
                  >
                    <CheckCircleIcon
                      :class="[
                        'w-5 h-5',
                        form.tags.length
                          ? 'text-emerald-500'
                          : 'text-foreground-muted',
                      ]"
                    />
                    {{ t("backupTasks.wizard.tagsReady") }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-else-if="step === 2" class="space-y-5">
            <div class="rounded-xl border border-border bg-background/30 p-4">
              <p class="text-sm font-semibold text-foreground mb-3">
                {{ t("backupTasks.form.sourceType") }}
              </p>
              <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                <button
                  v-for="kind in sourceKinds"
                  :key="kind.value"
                  type="button"
                  :class="[
                    'rounded-xl border p-4 text-left transition-colors',
                    form.source_kind === kind.value
                      ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                      : 'border-border bg-background/50 hover:bg-hover',
                  ]"
                  @click="form.source_kind = kind.value"
                >
                  <component
                    :is="kind.icon"
                    class="w-6 h-6 text-blue-500 mb-2"
                  />
                  <div class="flex items-center justify-between gap-2">
                    <p class="font-medium text-foreground">
                      {{ kind.label }}
                    </p>
                    <span class="text-xs text-foreground-secondary">
                      {{ kind.count }}
                    </span>
                  </div>
                  <p class="mt-1 text-sm text-foreground-secondary">
                    {{ kind.description }}
                  </p>
                </button>
              </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-5">
              <div
                class="rounded-xl border border-border bg-background/30 overflow-hidden"
              >
                <div class="p-3 border-b border-border">
                  <div class="relative">
                    <MagnifyingGlassIcon
                      class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground-muted"
                    />
                    <input
                      v-model="searchQuery"
                      class="w-full pl-9 pr-3 py-2 rounded-lg border border-border bg-background/50 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                      :placeholder="t('backupTasks.placeholders.searchSource')"
                    />
                  </div>
                </div>
                <div class="max-h-[360px] overflow-y-auto p-2 space-y-2">
                  <button
                    v-for="source in filteredSources"
                    :key="source.id"
                    type="button"
                    :class="[
                      'w-full rounded-lg border p-3 text-left transition-colors',
                      form.source_resource === source.id
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                        : 'border-border bg-background/50 hover:bg-hover',
                    ]"
                    @click="selectSource(source)"
                  >
                    <div class="flex items-start gap-3">
                      <FolderIcon class="w-5 h-5 text-blue-500 mt-0.5" />
                      <div class="min-w-0 flex-1">
                        <p class="font-medium text-foreground truncate">
                          {{ source.name }}
                        </p>
                        <p class="text-xs text-foreground-secondary truncate">
                          {{
                            source.resource_type_display || source.resource_type
                          }}
                        </p>
                        <p class="mt-1 text-xs text-foreground-muted truncate">
                          {{
                            sourceNodeName(source) ||
                            t("sourceResources.noBoundNode")
                          }}
                        </p>
                      </div>
                      <span
                        :class="[
                          'h-2 w-2 rounded-full mt-1.5',
                          sourceNodeStatus(source) === 'online'
                            ? 'bg-emerald-500'
                            : 'bg-foreground-muted',
                        ]"
                      />
                    </div>
                  </button>
                  <div
                    v-if="filteredSources.length === 0"
                    class="py-10 text-center text-sm text-foreground-secondary"
                  >
                    {{ t("backupTasks.wizard.noSources") }}
                  </div>
                </div>
              </div>

              <div class="space-y-4">
                <div
                  class="rounded-xl border border-border bg-background/30 overflow-hidden"
                >
                  <div
                    class="px-4 py-3 border-b border-border flex items-center justify-between"
                  >
                    <div>
                      <p class="text-sm font-semibold text-foreground">
                        {{ t("backupTasks.form.sourcePaths") }}
                      </p>
                      <p class="text-xs text-foreground-secondary">
                        {{ selectedSource?.name || "-" }}
                      </p>
                    </div>
                    <button
                      type="button"
                      class="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm text-foreground hover:bg-hover disabled:opacity-50"
                      :disabled="!selectedSource || directoryLoading"
                      @click="fetchDirectories(currentPath)"
                    >
                      <ArrowPathIcon
                        :class="[
                          'w-4 h-4',
                          directoryLoading ? 'animate-spin' : '',
                        ]"
                      />
                      {{ t("common.refresh") }}
                    </button>
                  </div>
                  <div
                    class="px-4 py-2 border-b border-border bg-background-secondary/50 flex items-center justify-between gap-3"
                  >
                    <code class="text-xs text-foreground break-all">
                      {{ currentPath || rootPath }}
                    </code>
                    <button
                      type="button"
                      class="text-xs text-blue-600 dark:text-blue-400 hover:underline disabled:text-foreground-muted"
                      :disabled="!currentPath || currentPath === '/'"
                      @click="navigateUp"
                    >
                      {{ t("repository.local.goUp") }}
                    </button>
                  </div>
                  <div class="max-h-56 overflow-y-auto">
                    <div
                      v-if="directoryLoading"
                      class="py-10 text-center text-sm text-foreground-secondary"
                    >
                      {{ t("common.loading") }}
                    </div>
                    <div
                      v-else-if="directoryError"
                      class="py-8 px-4 text-sm text-red-600 dark:text-red-400"
                    >
                      {{ directoryError }}
                    </div>
                    <div
                      v-else-if="directories.length === 0"
                      class="py-10 text-center text-sm text-foreground-secondary"
                    >
                      {{ t("backupTasks.wizard.noDirectories") }}
                    </div>
                    <div v-else class="divide-y divide-border">
                      <div
                        v-for="dir in directories"
                        :key="dir.path"
                        class="flex items-center gap-3 px-4 py-2 hover:bg-hover"
                      >
                        <input
                          type="checkbox"
                          class="rounded border-border"
                          :checked="form.backup_paths.includes(dir.path)"
                          @change="togglePath(dir.path)"
                        />
                        <button
                          type="button"
                          class="min-w-0 flex-1 flex items-center gap-2 text-left"
                          @click="navigateDirectory(dir.path)"
                        >
                          <FolderIcon class="w-4 h-4 text-blue-500 shrink-0" />
                          <span class="text-sm text-foreground truncate">
                            {{ dir.name }}
                          </span>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <label class="block">
                    <span class="text-sm font-medium text-foreground">
                      {{ t("backupTasks.wizard.selectedPaths") }}
                    </span>
                    <textarea
                      v-model="includePathsText"
                      rows="5"
                      class="mt-1 w-full px-3 py-2 rounded-lg border border-border bg-background/50 text-foreground font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="/data&#10;/home/app"
                    />
                  </label>
                  <label class="block">
                    <span class="text-sm font-medium text-foreground">
                      {{ t("backupTasks.form.excludePaths") }}
                    </span>
                    <textarea
                      v-model="excludePatternsText"
                      rows="5"
                      class="mt-1 w-full px-3 py-2 rounded-lg border border-border bg-background/50 text-foreground font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="*.tmp, *.log, /temp/"
                    />
                  </label>
                </div>
              </div>
            </div>
          </div>

          <div v-else-if="step === 3" class="space-y-5">
            <div class="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-5">
              <div class="space-y-3">
                <p class="text-sm font-semibold text-foreground">
                  {{ t("backupTasks.wizard.backupRepository") }}
                </p>
                <button
                  v-for="repo in repositories"
                  :key="repo.id"
                  type="button"
                  :class="[
                    'w-full rounded-xl border p-4 text-left transition-colors',
                    form.target_repository === repo.id
                      ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                      : 'border-border bg-background/50 hover:bg-hover',
                  ]"
                  @click="form.target_repository = repo.id"
                >
                  <div class="flex items-center justify-between gap-4">
                    <div class="flex items-center gap-3 min-w-0">
                      <CircleStackIcon class="w-6 h-6 text-blue-500 shrink-0" />
                      <div class="min-w-0">
                        <p class="font-medium text-foreground truncate">
                          {{ repo.name }}
                        </p>
                        <p class="text-sm text-foreground-secondary">
                          {{ repo.repo_type }} · {{ repo.status }}
                        </p>
                        <p class="mt-1 text-xs text-foreground-muted truncate">
                          {{
                            repo.repo_type === "s3"
                              ? repo.config?.endpoint ||
                                repo.config?.bucket ||
                                "-"
                              : repo.repo_type === "local"
                                ? repo.config?.path || "-"
                                : repo.config?.server ||
                                  repo.config?.export_path ||
                                  "-"
                          }}
                        </p>
                      </div>
                    </div>
                    <CheckCircleIcon
                      v-if="form.target_repository === repo.id"
                      class="w-5 h-5 text-blue-500 shrink-0"
                    />
                  </div>
                </button>
              </div>
              <div
                class="rounded-xl border border-border bg-background/30 p-4 space-y-4"
              >
                <p class="text-sm font-semibold text-foreground">
                  {{ t("backupTasks.wizard.repositoryDetails") }}
                </p>
                <div
                  v-if="selectedRepository"
                  class="rounded-lg border border-border bg-background/50 divide-y divide-border"
                >
                  <div
                    v-for="row in repositoryDetails"
                    :key="row.label"
                    class="px-3 py-2"
                  >
                    <p class="text-xs text-foreground-secondary">
                      {{ row.label }}
                    </p>
                    <p
                      class="mt-1 text-sm font-medium text-foreground break-all"
                    >
                      {{ row.value || "-" }}
                    </p>
                  </div>
                </div>
                <div
                  v-else
                  class="rounded-lg border border-border bg-background/50 p-4 text-sm text-foreground-secondary"
                >
                  {{ t("backupTasks.wizard.selectRepositoryHint") }}
                </div>
                <div>
                  <p class="text-xs text-foreground-secondary">
                    {{ t("backupTasks.wizard.repositoryCapacity") }}
                  </p>
                  <p class="mt-1 text-sm font-medium text-foreground">
                    {{ repositoryCapacity }}
                  </p>
                </div>
                <label class="block">
                  <span class="text-sm font-medium text-foreground">
                    {{ t("policies.form.compression") }}
                  </span>
                  <select
                    v-model="form.compression_type"
                    class="mt-1 w-full px-3 py-2 rounded-lg border border-border bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="zstd">zstd</option>
                    <option value="gzip">gzip</option>
                    <option value="none">{{ t("common.none") }}</option>
                  </select>
                </label>
                <label class="flex items-center gap-2 text-sm text-foreground">
                  <input
                    v-model="form.encryption_enabled"
                    type="checkbox"
                    class="rounded border-border"
                  />
                  {{ t("policies.form.encryption") }}
                </label>
              </div>
            </div>
          </div>

          <div v-else-if="step === 4" class="space-y-5">
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <div
                class="rounded-xl border border-border bg-background/30 p-4 space-y-4"
              >
                <div class="flex items-center gap-2">
                  <ClockIcon class="w-5 h-5 text-blue-500" />
                  <p class="text-sm font-semibold text-foreground">
                    {{ t("backupTasks.form.schedule") }}
                  </p>
                </div>
                <label class="flex items-center gap-2 text-sm text-foreground">
                  <input
                    v-model="form.schedule_mode"
                    type="radio"
                    value="manual"
                    class="border-border"
                  />
                  {{ t("backupTasks.schedule.manual") }}
                </label>
                <label class="flex items-center gap-2 text-sm text-foreground">
                  <input
                    v-model="form.schedule_mode"
                    type="radio"
                    value="interval"
                    class="border-border"
                  />
                  {{ t("backupTasks.schedule.interval") }}
                </label>
                <div
                  v-if="form.schedule_mode === 'interval'"
                  class="grid grid-cols-[120px_1fr] gap-3 pl-6"
                >
                  <input
                    v-model.number="form.interval_value"
                    type="number"
                    min="1"
                    class="px-3 py-2 rounded-lg border border-border bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <select
                    v-model="form.interval_unit"
                    class="px-3 py-2 rounded-lg border border-border bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="minutes">
                      {{ t("backupTasks.schedule.units.minutes") }}
                    </option>
                    <option value="hours">
                      {{ t("backupTasks.schedule.units.hours") }}
                    </option>
                    <option value="days">
                      {{ t("backupTasks.schedule.units.days") }}
                    </option>
                  </select>
                </div>
                <label class="flex items-center gap-2 text-sm text-foreground">
                  <input
                    v-model="form.schedule_mode"
                    type="radio"
                    value="cron"
                    class="border-border"
                  />
                  {{ t("backupTasks.schedule.cron") }}
                </label>
                <input
                  v-if="form.schedule_mode === 'cron'"
                  v-model="form.cron_expression"
                  class="ml-6 w-[calc(100%-1.5rem)] px-3 py-2 rounded-lg border border-border bg-background/50 text-foreground font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="0 */4 * * *"
                />
              </div>

              <div
                class="rounded-xl border border-border bg-background/30 p-4 space-y-4"
              >
                <div class="flex items-center gap-2">
                  <ShieldCheckIcon class="w-5 h-5 text-blue-500" />
                  <p class="text-sm font-semibold text-foreground">
                    {{ t("backupTasks.retention.title") }}
                  </p>
                </div>
                <label class="flex items-center gap-2 text-sm text-foreground">
                  <input
                    v-model="form.retention_mode"
                    type="radio"
                    value="policy"
                    class="border-border"
                  />
                  {{ t("backupTasks.retention.policy") }}
                </label>
                <select
                  v-if="form.retention_mode === 'policy'"
                  v-model="form.schedule"
                  class="ml-6 w-[calc(100%-1.5rem)] px-3 py-2 rounded-lg border border-border bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">{{ t("backupTasks.form.noPolicy") }}</option>
                  <option
                    v-for="policy in policies"
                    :key="policy.id"
                    :value="policy.id"
                  >
                    {{ policy.name }}
                  </option>
                </select>
                <label class="flex items-center gap-2 text-sm text-foreground">
                  <input
                    v-model="form.retention_mode"
                    type="radio"
                    value="custom"
                    class="border-border"
                  />
                  {{ t("backupTasks.retention.custom") }}
                </label>
                <div
                  v-if="form.retention_mode === 'custom'"
                  class="grid grid-cols-1 md:grid-cols-2 gap-3 pl-6"
                >
                  <label class="block">
                    <span class="text-xs text-foreground-secondary">
                      {{ t("backupTasks.form.maxSnapshots") }}
                    </span>
                    <input
                      v-model.number="form.max_snapshots"
                      type="number"
                      min="1"
                      class="mt-1 w-full px-3 py-2 rounded-lg border border-border bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </label>
                  <label class="block">
                    <span class="text-xs text-foreground-secondary">
                      {{ t("backupTasks.form.retentionDays") }}
                    </span>
                    <input
                      v-model.number="form.retention_days"
                      type="number"
                      min="1"
                      class="mt-1 w-full px-3 py-2 rounded-lg border border-border bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </label>
                </div>
              </div>
            </div>
          </div>

          <div v-else class="space-y-5">
            <div class="rounded-xl border border-border bg-background/30 p-5">
              <p class="text-sm font-semibold text-foreground mb-4">
                {{ t("backupTasks.wizard.reviewTitle") }}
              </p>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div
                  class="rounded-lg border border-border bg-background/50 p-3"
                >
                  <p class="text-xs text-foreground-secondary">
                    {{ t("backupTasks.wizard.basic") }}
                  </p>
                  <p class="mt-1 font-medium text-foreground">
                    {{ form.name }}
                  </p>
                  <p class="mt-1 text-xs text-foreground-muted">
                    {{ form.tags.join(", ") || "-" }}
                  </p>
                </div>
                <div
                  class="rounded-lg border border-border bg-background/50 p-3"
                >
                  <p class="text-xs text-foreground-secondary">
                    {{ t("backupTasks.wizard.source") }}
                  </p>
                  <p class="mt-1 font-medium text-foreground">
                    {{ selectedSource?.name || "-" }}
                  </p>
                  <p class="mt-1 text-xs text-foreground-muted">
                    {{ sourceNodeName(selectedSource) || "-" }}
                  </p>
                </div>
                <div
                  class="rounded-lg border border-border bg-background/50 p-3"
                >
                  <p class="text-xs text-foreground-secondary">
                    {{ t("backupTasks.wizard.backupRepository") }}
                  </p>
                  <p class="mt-1 font-medium text-foreground">
                    {{ selectedRepository?.name || "-" }}
                  </p>
                  <p class="mt-1 text-xs text-foreground-muted">
                    {{ repositoryCapacity }}
                  </p>
                </div>
                <div
                  class="rounded-lg border border-border bg-background/50 p-3"
                >
                  <p class="text-xs text-foreground-secondary">
                    {{ t("backupTasks.wizard.scheduleRetention") }}
                  </p>
                  <p class="mt-1 font-medium text-foreground">
                    {{ scheduleSummary }}
                  </p>
                  <p class="mt-1 text-xs text-foreground-muted">
                    {{ retentionSummary }}
                  </p>
                </div>
              </div>
              <div class="mt-4">
                <p class="text-sm font-medium text-foreground mb-2">
                  {{ t("backupTasks.wizard.selectedPaths") }}
                </p>
                <div class="flex flex-wrap gap-2">
                  <span
                    v-for="path in form.backup_paths"
                    :key="path"
                    class="px-2 py-1 rounded bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 text-xs font-mono"
                  >
                    {{ path }}
                  </span>
                </div>
              </div>
            </div>

            <div
              class="rounded-xl border border-border bg-background/30 p-4 flex flex-wrap gap-4 text-sm text-foreground-secondary"
            >
              <span class="inline-flex items-center gap-2">
                <CheckCircleIcon class="w-5 h-5 text-emerald-500" />
                {{ t("backupTasks.diagnostics.sourceOnline") }}
              </span>
              <span class="inline-flex items-center gap-2">
                <CheckCircleIcon class="w-5 h-5 text-emerald-500" />
                {{ t("backupTasks.diagnostics.repositoryReady") }}
              </span>
              <span class="inline-flex items-center gap-2">
                <ExclamationCircleIcon class="w-5 h-5 text-amber-500" />
                {{ t("backupTasks.diagnostics.permissionsAfterSave") }}
              </span>
            </div>
          </div>
        </div>

        <div
          class="px-6 py-4 border-t border-border bg-card flex justify-between flex-shrink-0"
        >
          <button
            class="px-4 py-2 text-sm rounded-lg border border-border text-foreground hover:bg-hover disabled:opacity-50"
            :disabled="step === 1"
            @click="step--"
          >
            {{ t("common.back") }}
          </button>
          <div class="flex gap-2">
            <button
              class="px-4 py-2 text-sm rounded-lg border border-border text-foreground hover:bg-hover"
              @click="emit('close')"
            >
              {{ t("common.cancel") }}
            </button>
            <button
              v-if="step < 5"
              class="px-5 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
              :disabled="!canNext"
              @click="step++"
            >
              {{ t("common.next") }}
            </button>
            <button
              v-else
              class="px-5 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
              :disabled="!canNext"
              @click="save"
            >
              {{ t("common.create") }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
