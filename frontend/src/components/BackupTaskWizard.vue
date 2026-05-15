<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import {
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
type RetentionFieldKey =
  | "keep_latest"
  | "keep_hourly"
  | "keep_daily"
  | "keep_weekly"
  | "keep_monthly"
  | "keep_annual";

const step = ref(1);
const searchQuery = ref("");
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
  retention_mode: "custom" as RetentionMode,
  schedule: "" as string,
  override_schedule: false,
  override_retention: false,
  retention_days: 30,
  max_snapshots: 10,
  keep_latest: 10,
  keep_hourly: 0,
  keep_daily: 30,
  keep_weekly: 0,
  keep_monthly: 0,
  keep_annual: 0,
  dot_ignore_files: [".kopiaignore"] as string[],
  one_file_system: false,
  ignore_file_errors: false,
  ignore_dir_errors: false,
  compression_enabled: true,
  encryption_enabled: true,
  compression_type: "zstd",
  compression_level: 6,
  max_concurrent_files: 4,
  metadata_compression: true,
  ignore_identical_snapshots: true,
});

const steps = computed(() => [
  t("backupTasks.wizard.basic"),
  t("backupTasks.wizard.source"),
  t("backupTasks.wizard.backupRepository"),
  t("backupTasks.wizard.scheduleRetention"),
  t("backupTasks.wizard.review"),
]);

const retentionFields: Array<{ key: RetentionFieldKey; label: string }> = [
  { key: "keep_latest", label: "latest" },
  { key: "keep_hourly", label: "hourly" },
  { key: "keep_daily", label: "daily" },
  { key: "keep_weekly", label: "weekly" },
  { key: "keep_monthly", label: "monthly" },
  { key: "keep_annual", label: "annual" },
];

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

const sourceProtectionPaths = computed(() => {
  const source = selectedSource.value;
  if (!source) return [];
  const config = source.config || {};
  if (source.resource_type === "local") {
    return [config.root_path || config.path || "/"];
  }
  if (source.resource_type === "s3") {
    return [config.prefix || "/"];
  }
  if (["nas", "nfs", "cifs"].includes(source.resource_type)) {
    return [
      source.mount_point ||
        (config as any).mount_point ||
        config.export_path ||
        config.share ||
        "/",
    ];
  }
  return ["/"];
});

const sourceDetails = computed(() => {
  const source = selectedSource.value;
  if (!source) return [];
  const config = source.config || {};
  const rows: Array<{ label: string; value: string }> = [
    {
      label: t("backupTasks.sourceDetails.type"),
      value: source.resource_type_display || source.resource_type,
    },
    {
      label: t("backupTasks.sourceDetails.status"),
      value: source.status_display || source.status || "-",
    },
    {
      label: t("backupTasks.sourceDetails.boundNode"),
      value: sourceNodeName(source) || "-",
    },
  ];

  if (source.resource_type === "local") {
    rows.push({
      label: t("backupTasks.sourceDetails.path"),
      value: config.root_path || config.path || "/",
    });
  } else if (source.resource_type === "s3") {
    rows.push(
      {
        label: t("backupTasks.sourceDetails.endpoint"),
        value: config.endpoint || "-",
      },
      {
        label: t("backupTasks.sourceDetails.bucket"),
        value: config.bucket || "-",
      },
      {
        label: t("backupTasks.sourceDetails.prefix"),
        value: config.prefix || "/",
      },
      {
        label: t("backupTasks.sourceDetails.region"),
        value: config.region || "-",
      },
    );
  } else {
    rows.push(
      {
        label: t("backupTasks.sourceDetails.endpoint"),
        value:
          config.server && (config.export_path || config.share)
            ? `${config.server}:${config.export_path || config.share}`
            : config.server || "-",
      },
      {
        label: t("backupTasks.sourceDetails.mountPoint"),
        value: source.mount_point || (config as any).mount_point || "-",
      },
      {
        label: t("backupTasks.sourceDetails.mountOptions"),
        value: config.mount_options || "-",
      },
    );
  }

  rows.push(
    {
      label: t("backupTasks.sourceDetails.capacity"),
      value: source.total_size
        ? `${formatBytes(source.used_size)} / ${formatBytes(source.total_size)}`
        : t("backupTasks.wizard.capacityUnknown"),
    },
    {
      label: t("backupTasks.sourceDetails.files"),
      value: String(source.file_count || 0),
    },
  );
  return rows;
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

const dotIgnoreFilesText = computed({
  get: () => form.dot_ignore_files.join("\n"),
  set: (value: string) => {
    form.dot_ignore_files = value
      .split(/[\n,]+/)
      .map((item) => item.trim())
      .filter(Boolean);
  },
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
    snapshots: form.keep_latest,
    days: form.keep_daily,
  });
});

const policyOverrideSummary = computed(() => {
  const values = [];
  if (form.override_schedule)
    values.push(t("backupTasks.policyOverrides.schedule"));
  if (form.override_retention || form.retention_mode === "custom") {
    values.push(t("backupTasks.policyOverrides.retention"));
  }
  if (
    form.exclude_patterns.length ||
    form.dot_ignore_files.length ||
    form.one_file_system ||
    form.ignore_file_errors ||
    form.ignore_dir_errors
  ) {
    values.push(t("backupTasks.policyOverrides.files"));
  }
  values.push(t("backupTasks.policyOverrides.compression"));
  return values.length
    ? values.join(" / ")
    : t("backupTasks.policyOverrides.none");
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
    return form.keep_latest >= 0 && form.keep_daily >= 0;
  }
  return true;
});

watch(
  () => form.source_kind,
  () => {
    form.source_resource = "";
    form.backup_paths = [];
  },
);

watch(
  () => form.source_resource,
  () => {
    form.backup_paths = [...sourceProtectionPaths.value];
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
  form.backup_paths = [...sourceProtectionPaths.value];
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
  const policyOverrides: Record<string, any> = {
    file_policy: {
      override: true,
      ignore_patterns: [...form.exclude_patterns],
      additional_ignore_patterns: [],
      dot_ignore_files: [...form.dot_ignore_files],
      one_file_system: form.one_file_system,
      ignore_file_errors: form.ignore_file_errors,
      ignore_dir_errors: form.ignore_dir_errors,
    },
  };

  if (form.override_schedule || !schedule) {
    policyOverrides.snapshot_schedule = {
      override: true,
      mode: form.schedule_mode,
      interval:
        form.schedule_mode === "interval"
          ? `${form.interval_value}${form.interval_unit === "minutes" ? "m" : form.interval_unit === "hours" ? "h" : "d"}`
          : "",
      time_of_day: "",
      cron: form.schedule_mode === "cron" ? form.cron_expression.trim() : "",
      run_missed: true,
    };
  }

  if (
    form.override_retention ||
    form.retention_mode === "custom" ||
    !schedule
  ) {
    policyOverrides.retention_policy = {
      override: true,
      keep_latest: form.keep_latest,
      keep_hourly: form.keep_hourly,
      keep_daily: form.keep_daily,
      keep_weekly: form.keep_weekly,
      keep_monthly: form.keep_monthly,
      keep_annual: form.keep_annual,
    };
  }

  policyOverrides.compression_policy = {
    override: true,
    compression: form.compression_enabled ? form.compression_type : "none",
    metadata_compression: form.metadata_compression,
    max_parallel_file_reads: form.max_concurrent_files,
    ignore_identical_snapshots: form.ignore_identical_snapshots,
  };

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
    compression_level: form.compression_level,
    max_concurrent_files: form.max_concurrent_files,
    encryption_enabled: form.encryption_enabled,
    schedule,
    policy_overrides: policyOverrides,
    retention_days: form.keep_daily,
    max_snapshots: form.keep_latest,
  });
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/50" @click="emit('close')" />
      <div
        class="relative modal-surface rounded-2xl shadow-xl w-full max-w-5xl max-h-[92vh] flex flex-col">
        <div
          class="px-6 py-4 border-b border-border flex items-center justify-between flex-shrink-0">
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
                @click="step = index + 1">
                <span
                  :class="[
                    'w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold',
                    step === index + 1
                      ? 'bg-white/20'
                      : step > index + 1
                        ? 'bg-emerald-100 dark:bg-emerald-900/40'
                        : 'bg-background-secondary',
                  ]">
                  {{ index + 1 }}
                </span>
                <span class="text-xs font-medium whitespace-nowrap">
                  {{ item }}
                </span>
              </button>
              <div
                v-if="index < steps.length - 1"
                class="h-px w-8 shrink-0 bg-border" />
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
                    class="mt-1 w-full px-3 py-2 rounded-lg border border-border bg-background/50 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    :placeholder="t('backupTasks.placeholders.taskName')" />
                </label>
                <label class="block">
                  <span class="text-sm font-medium text-foreground">
                    {{ t("common.description") }}
                  </span>
                  <textarea
                    v-model="form.description"
                    rows="4"
                    class="mt-1 w-full px-3 py-2 rounded-lg border border-border bg-background/50 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    :placeholder="t('backupTasks.placeholders.description')" />
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
                      @click="removeTag(tag)">
                      <TagIcon class="w-3.5 h-3.5" />
                      {{ tag }}
                      <XMarkIcon class="w-3.5 h-3.5 text-foreground-muted" />
                    </button>
                    <form class="flex gap-2" @submit.prevent="addTag">
                      <input
                        v-model="tagInput"
                        class="w-32 px-3 py-1 rounded-full border border-border bg-background/50 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        :placeholder="t('backupTasks.placeholders.addTag')" />
                    </form>
                  </div>
                </div>
              </div>
              <div
                class="rounded-xl border border-border bg-background/30 p-4 space-y-3">
                <p class="text-sm font-semibold text-foreground">
                  {{ t("backupTasks.wizard.basicChecklist") }}
                </p>
                <div class="space-y-2 text-sm">
                  <div
                    class="flex items-center gap-2 text-foreground-secondary">
                    <CheckCircleIcon
                      :class="[
                        'w-5 h-5',
                        form.name.trim()
                          ? 'text-emerald-500'
                          : 'text-foreground-muted',
                      ]" />
                    {{ t("backupTasks.wizard.nameReady") }}
                  </div>
                  <div
                    class="flex items-center gap-2 text-foreground-secondary">
                    <CheckCircleIcon
                      :class="[
                        'w-5 h-5',
                        form.description.trim()
                          ? 'text-emerald-500'
                          : 'text-foreground-muted',
                      ]" />
                    {{ t("backupTasks.wizard.descriptionReady") }}
                  </div>
                  <div
                    class="flex items-center gap-2 text-foreground-secondary">
                    <CheckCircleIcon
                      :class="[
                        'w-5 h-5',
                        form.tags.length
                          ? 'text-emerald-500'
                          : 'text-foreground-muted',
                      ]" />
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
                  @click="form.source_kind = kind.value">
                  <component
                    :is="kind.icon"
                    class="w-6 h-6 text-blue-500 mb-2" />
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
                class="rounded-xl border border-border bg-background/30 overflow-hidden">
                <div class="p-3 border-b border-border">
                  <div class="relative">
                    <MagnifyingGlassIcon
                      class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground-muted" />
                    <input
                      v-model="searchQuery"
                      class="w-full pl-9 pr-3 py-2 rounded-lg border border-border bg-background/50 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                      :placeholder="
                        t('backupTasks.placeholders.searchSource')
                      " />
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
                    @click="selectSource(source)">
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
                        ]" />
                    </div>
                  </button>
                  <div
                    v-if="filteredSources.length === 0"
                    class="py-10 text-center text-sm text-foreground-secondary">
                    {{ t("backupTasks.wizard.noSources") }}
                  </div>
                </div>
              </div>

              <div class="space-y-4">
                <div
                  class="rounded-xl border border-border bg-background/30 p-4 space-y-4">
                  <div class="flex items-start justify-between gap-4">
                    <div>
                      <p class="text-sm font-semibold text-foreground">
                        {{ t("backupTasks.sourceDetails.title") }}
                      </p>
                      <p class="mt-1 text-xs text-foreground-secondary">
                        {{ t("backupTasks.sourceDetails.fixedScopeDesc") }}
                      </p>
                    </div>
                    <span
                      v-if="selectedSource"
                      :class="[
                        'rounded-full px-2 py-1 text-xs font-medium',
                        sourceNodeStatus(selectedSource) === 'online'
                          ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300'
                          : 'bg-background-secondary text-foreground-secondary',
                      ]">
                      {{ sourceNodeStatus(selectedSource) || "-" }}
                    </span>
                  </div>
                  <div
                    v-if="selectedSource"
                    class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div
                      v-for="row in sourceDetails"
                      :key="row.label"
                      class="rounded-lg border border-border bg-background/50 p-3">
                      <p class="text-xs text-foreground-secondary">
                        {{ row.label }}
                      </p>
                      <p
                        class="mt-1 text-sm font-medium text-foreground break-all">
                        {{ row.value || "-" }}
                      </p>
                    </div>
                  </div>
                  <div
                    v-else
                    class="rounded-lg border border-border bg-background/50 p-4 text-sm text-foreground-secondary">
                    {{ t("backupTasks.sourceDetails.selectHint") }}
                  </div>
                  <div
                    v-if="selectedSource"
                    class="rounded-lg border border-blue-200 bg-blue-50/70 p-3 dark:border-blue-900/40 dark:bg-blue-900/20">
                    <p
                      class="text-xs font-medium text-blue-700 dark:text-blue-300">
                      {{ t("backupTasks.sourceDetails.protectedScope") }}
                    </p>
                    <div class="mt-2 flex flex-wrap gap-2">
                      <code
                        v-for="path in sourceProtectionPaths"
                        :key="path"
                        class="rounded bg-white/70 px-2 py-1 text-xs text-blue-800 dark:bg-blue-950/40 dark:text-blue-200">
                        {{ path }}
                      </code>
                    </div>
                  </div>
                </div>

                <div class="grid grid-cols-1 gap-4">
                  <div
                    class="rounded-xl border border-border bg-background/30 p-4 space-y-3">
                    <p class="text-sm font-semibold text-foreground">
                      {{ t("backupTasks.files.title") }}
                    </p>
                    <label class="block">
                      <span
                        class="text-xs font-medium text-foreground-secondary">
                        {{ t("backupTasks.files.exclusionPatterns") }}
                      </span>
                      <textarea
                        v-model="excludePatternsText"
                        rows="4"
                        class="mt-1 w-full px-3 py-2 rounded-lg border border-border bg-background/50 text-foreground font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="*.tmp&#10;node_modules/**&#10;.cache/&#10;*.log" />
                      <p
                        class="mt-1 text-[11px] leading-4 text-foreground-muted">
                        {{ t("backupTasks.files.exclusionPatternsDesc") }}
                      </p>
                    </label>
                    <label class="block">
                      <span
                        class="text-xs font-medium text-foreground-secondary">
                        {{ t("backupTasks.files.dotIgnoreFiles") }}
                      </span>
                      <textarea
                        v-model="dotIgnoreFilesText"
                        rows="2"
                        class="mt-1 w-full px-3 py-2 rounded-lg border border-border bg-background/50 text-foreground font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder=".kopiaignore" />
                      <p
                        class="mt-1 text-[11px] leading-4 text-foreground-muted">
                        {{ t("backupTasks.files.dotIgnoreFilesDesc") }}
                      </p>
                    </label>
                    <label
                      class="flex items-start gap-2 text-sm text-foreground">
                      <input
                        v-model="form.one_file_system"
                        type="checkbox"
                        class="mt-1 rounded border-border" />
                      <span>
                        {{ t("backupTasks.files.oneFileSystem") }}
                        <span
                          class="block text-[11px] leading-4 text-foreground-muted">
                          {{ t("backupTasks.files.oneFileSystemDesc") }}
                        </span>
                      </span>
                    </label>
                    <label
                      class="flex items-start gap-2 text-sm text-foreground">
                      <input
                        v-model="form.ignore_file_errors"
                        type="checkbox"
                        class="mt-1 rounded border-border" />
                      <span>
                        {{ t("backupTasks.files.ignoreFileErrors") }}
                        <span
                          class="block text-[11px] leading-4 text-foreground-muted">
                          {{ t("backupTasks.files.ignoreFileErrorsDesc") }}
                        </span>
                      </span>
                    </label>
                    <label
                      class="flex items-start gap-2 text-sm text-foreground">
                      <input
                        v-model="form.ignore_dir_errors"
                        type="checkbox"
                        class="mt-1 rounded border-border" />
                      <span>
                        {{ t("backupTasks.files.ignoreDirErrors") }}
                        <span
                          class="block text-[11px] leading-4 text-foreground-muted">
                          {{ t("backupTasks.files.ignoreDirErrorsDesc") }}
                        </span>
                      </span>
                    </label>
                  </div>
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
                  @click="form.target_repository = repo.id">
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
                      class="w-5 h-5 text-blue-500 shrink-0" />
                  </div>
                </button>
              </div>
              <div
                class="rounded-xl border border-border bg-background/30 p-4 space-y-4">
                <p class="text-sm font-semibold text-foreground">
                  {{ t("backupTasks.wizard.repositoryDetails") }}
                </p>
                <div
                  v-if="selectedRepository"
                  class="rounded-lg border border-border bg-background/50 divide-y divide-border">
                  <div
                    v-for="row in repositoryDetails"
                    :key="row.label"
                    class="px-3 py-2">
                    <p class="text-xs text-foreground-secondary">
                      {{ row.label }}
                    </p>
                    <p
                      class="mt-1 text-sm font-medium text-foreground break-all">
                      {{ row.value || "-" }}
                    </p>
                  </div>
                </div>
                <div
                  v-else
                  class="rounded-lg border border-border bg-background/50 p-4 text-sm text-foreground-secondary">
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
                <label class="flex items-center gap-2 text-sm text-foreground">
                  <input
                    v-model="form.encryption_enabled"
                    type="checkbox"
                    class="rounded border-border" />
                  {{ t("policies.form.encryption") }}
                </label>
              </div>
            </div>

            <div
              class="rounded-xl border border-border bg-background/30 p-4 space-y-3">
              <p class="text-sm font-semibold text-foreground">
                {{ t("backupTasks.compression.title") }}
              </p>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <label class="block">
                  <span class="text-xs text-foreground-secondary">
                    {{ t("backupTasks.compression.algorithm") }}
                  </span>
                  <select
                    v-model="form.compression_type"
                    class="mt-1 w-full px-3 py-2 rounded-lg border border-border bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500">
                    <option value="zstd">zstd</option>
                    <option value="gzip">gzip</option>
                    <option value="none">{{ t("common.none") }}</option>
                  </select>
                  <p class="mt-1 text-[11px] leading-4 text-foreground-muted">
                    {{ t("backupTasks.compression.algorithmDesc") }}
                  </p>
                </label>
                <label class="block">
                  <span class="text-xs text-foreground-secondary">
                    {{ t("backupTasks.compression.parallelReads") }}
                  </span>
                  <input
                    v-model.number="form.max_concurrent_files"
                    type="number"
                    min="1"
                    class="mt-1 w-full px-3 py-2 rounded-lg border border-border bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500" />
                  <p class="mt-1 text-[11px] leading-4 text-foreground-muted">
                    {{ t("backupTasks.compression.parallelReadsDesc") }}
                  </p>
                </label>
              </div>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <label class="flex items-start gap-2 text-sm text-foreground">
                  <input
                    v-model="form.metadata_compression"
                    type="checkbox"
                    class="mt-1 rounded border-border" />
                  <span>
                    {{ t("backupTasks.compression.metadata") }}
                    <span
                      class="block text-[11px] leading-4 text-foreground-muted">
                      {{ t("backupTasks.compression.metadataDesc") }}
                    </span>
                  </span>
                </label>
                <label class="flex items-start gap-2 text-sm text-foreground">
                  <input
                    v-model="form.ignore_identical_snapshots"
                    type="checkbox"
                    class="mt-1 rounded border-border" />
                  <span>
                    {{ t("backupTasks.compression.ignoreIdentical") }}
                    <span
                      class="block text-[11px] leading-4 text-foreground-muted">
                      {{ t("backupTasks.compression.ignoreIdenticalDesc") }}
                    </span>
                  </span>
                </label>
              </div>
            </div>
          </div>

          <div v-else-if="step === 4" class="space-y-5">
            <div
              class="rounded-xl border border-border bg-background/30 p-4 space-y-3">
              <div class="flex items-start justify-between gap-4">
                <div>
                  <p class="text-sm font-semibold text-foreground">
                    {{ t("backupTasks.policyOverrides.policyBaseline") }}
                  </p>
                  <p class="mt-1 text-xs text-foreground-secondary">
                    {{ t("backupTasks.policyOverrides.policyBaselineDesc") }}
                  </p>
                </div>
                <span
                  class="rounded-full bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 dark:bg-blue-900/20 dark:text-blue-300">
                  {{ policyOverrideSummary }}
                </span>
              </div>
              <select
                v-model="form.schedule"
                class="w-full px-3 py-2 rounded-lg border border-border bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                @change="
                  form.retention_mode = form.schedule ? 'policy' : 'custom'
                ">
                <option value="">{{ t("backupTasks.form.noPolicy") }}</option>
                <option
                  v-for="policy in policies"
                  :key="policy.id"
                  :value="policy.id">
                  {{ policy.name }}
                </option>
              </select>
              <div
                v-if="selectedPolicy"
                class="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-foreground-secondary">
                <div
                  class="rounded-lg border border-border bg-background/50 p-2">
                  <span class="block text-foreground-muted">
                    {{ t("backupTasks.policyOverrides.schedule") }}
                  </span>
                  {{ selectedPolicy.snapshot_schedule?.mode || "-" }}
                </div>
                <div
                  class="rounded-lg border border-border bg-background/50 p-2">
                  <span class="block text-foreground-muted">
                    {{ t("backupTasks.policyOverrides.retention") }}
                  </span>
                  {{ selectedPolicy.retention_policy?.keep_latest || 0 }} latest
                </div>
              </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <div
                class="rounded-xl border border-border bg-background/30 p-4 space-y-4">
                <div class="flex items-center gap-2">
                  <ClockIcon class="w-5 h-5 text-blue-500" />
                  <p class="text-sm font-semibold text-foreground">
                    {{ t("backupTasks.form.schedule") }}
                  </p>
                </div>
                <label
                  v-if="selectedPolicy"
                  class="flex items-center gap-2 text-sm text-foreground">
                  <input
                    v-model="form.override_schedule"
                    type="checkbox"
                    class="rounded border-border" />
                  {{ t("backupTasks.policyOverrides.overrideSchedule") }}
                </label>
                <label class="flex items-center gap-2 text-sm text-foreground">
                  <input
                    v-model="form.schedule_mode"
                    type="radio"
                    value="manual"
                    class="border-border" />
                  {{ t("backupTasks.schedule.manual") }}
                </label>
                <label class="flex items-center gap-2 text-sm text-foreground">
                  <input
                    v-model="form.schedule_mode"
                    type="radio"
                    value="interval"
                    class="border-border" />
                  {{ t("backupTasks.schedule.interval") }}
                </label>
                <div
                  v-if="form.schedule_mode === 'interval'"
                  class="grid grid-cols-[120px_1fr] gap-3 pl-6">
                  <input
                    v-model.number="form.interval_value"
                    type="number"
                    min="1"
                    class="px-3 py-2 rounded-lg border border-border bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500" />
                  <select
                    v-model="form.interval_unit"
                    class="px-3 py-2 rounded-lg border border-border bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500">
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
                    class="border-border" />
                  {{ t("backupTasks.schedule.cron") }}
                </label>
                <input
                  v-if="form.schedule_mode === 'cron'"
                  v-model="form.cron_expression"
                  class="ml-6 w-[calc(100%-1.5rem)] px-3 py-2 rounded-lg border border-border bg-background/50 text-foreground font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="0 */4 * * *" />
              </div>

              <div
                class="rounded-xl border border-border bg-background/30 p-4 space-y-4">
                <div class="flex items-center gap-2">
                  <ShieldCheckIcon class="w-5 h-5 text-blue-500" />
                  <p class="text-sm font-semibold text-foreground">
                    {{ t("backupTasks.retention.title") }}
                  </p>
                </div>
                <template v-if="selectedPolicy">
                  <label
                    class="flex items-center gap-2 text-sm text-foreground">
                    <input
                      v-model="form.retention_mode"
                      type="radio"
                      value="policy"
                      class="border-border" />
                    {{ t("backupTasks.policyOverrides.usePolicyRetention") }}
                  </label>
                  <label
                    class="flex items-center gap-2 text-sm text-foreground">
                    <input
                      v-model="form.retention_mode"
                      type="radio"
                      value="custom"
                      class="border-border" />
                    {{ t("backupTasks.policyOverrides.overrideRetention") }}
                  </label>
                </template>
                <p v-else class="text-sm text-foreground-secondary">
                  {{ t("backupTasks.policyOverrides.taskRetentionDesc") }}
                </p>
                <div
                  v-if="form.retention_mode === 'custom' || !selectedPolicy"
                  :class="[
                    'grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3',
                    selectedPolicy ? 'pl-6' : '',
                  ]">
                  <label
                    v-for="field in retentionFields"
                    :key="field.key"
                    class="block">
                    <span class="text-xs text-foreground-secondary">
                      {{ t(`backupTasks.retention.${field.label}`) }}
                    </span>
                    <input
                      v-model.number="form[field.key]"
                      type="number"
                      min="0"
                      class="mt-1 w-full px-3 py-2 rounded-lg border border-border bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500" />
                    <p class="mt-1 text-[11px] leading-4 text-foreground-muted">
                      {{ t(`backupTasks.retention.${field.label}Desc`) }}
                    </p>
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
                  class="rounded-lg border border-border bg-background/50 p-3">
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
                  class="rounded-lg border border-border bg-background/50 p-3">
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
                  class="rounded-lg border border-border bg-background/50 p-3">
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
                  class="rounded-lg border border-border bg-background/50 p-3">
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
                    class="px-2 py-1 rounded bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 text-xs font-mono">
                    {{ path }}
                  </span>
                </div>
              </div>
            </div>

            <div
              class="rounded-xl border border-border bg-background/30 p-4 flex flex-wrap gap-4 text-sm text-foreground-secondary">
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
          class="px-6 py-4 border-t border-border bg-card flex justify-between flex-shrink-0">
          <button
            class="px-4 py-2 text-sm rounded-lg border border-border text-foreground hover:bg-hover disabled:opacity-50"
            :disabled="step === 1"
            @click="step--">
            {{ t("common.back") }}
          </button>
          <div class="flex gap-2">
            <button
              class="px-4 py-2 text-sm rounded-lg border border-border text-foreground hover:bg-hover"
              @click="emit('close')">
              {{ t("common.cancel") }}
            </button>
            <button
              v-if="step < 5"
              class="px-5 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
              :disabled="!canNext"
              @click="step++">
              {{ t("common.next") }}
            </button>
            <button
              v-else
              class="px-5 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
              :disabled="!canNext"
              @click="save">
              {{ t("common.create") }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
