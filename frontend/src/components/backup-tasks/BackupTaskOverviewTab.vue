<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  BoltIcon,
  ClockIcon,
  FolderIcon,
  ListBulletIcon,
  ServerStackIcon,
  ShieldCheckIcon,
} from "@heroicons/vue/24/outline";
import type { BackupTask } from "@/types/backup";
import type { Repository } from "@/types/repository";
import type { SourceResource } from "@/types/sourceResource";

defineProps<{
  task: BackupTask;
  source: SourceResource | null;
  repository: Repository | null;
  sourceRows: Array<[string, any]>;
  repositoryRows: Array<[string, any]>;
  formatDateTime: (value?: string | null) => string;
  formatBytes: (value: number) => string;
  formatSpeed: (value?: number | null) => string;
}>();

const { t } = useI18n();
</script>

<template>
  <div class="space-y-5">
    <section class="rounded-xl border border-border bg-card p-4 shadow-sm">
      <div class="mb-4 flex items-start gap-3">
        <span
          class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"
        >
          <ListBulletIcon class="h-5 w-5" />
        </span>
        <div>
          <h3 class="font-semibold text-foreground">
            {{ t("backupTasks.detail.basic") }}
          </h3>
          <p class="mt-0.5 text-xs text-foreground-secondary">
            {{ task.name }}
          </p>
        </div>
      </div>
      <dl class="grid grid-cols-1 gap-3 text-sm md:grid-cols-3">
        <div
          class="rounded-lg border border-border bg-background/50 p-3 md:col-span-3"
        >
          <dt class="text-xs font-medium text-foreground-secondary">
            {{ t("common.description") }}
          </dt>
          <dd class="mt-1 text-sm leading-6 text-foreground">
            {{ task.description || "-" }}
          </dd>
        </div>
        <div class="rounded-lg border border-border bg-background/50 p-3">
          <dt class="text-xs font-medium text-foreground-secondary">
            {{ t("backupTasks.form.taskType") }}
          </dt>
          <dd class="mt-1 text-sm font-medium text-foreground">
            {{ t(`backupTasks.types.${task.task_type || "full"}`) }}
          </dd>
        </div>
        <div class="rounded-lg border border-border bg-background/50 p-3">
          <dt class="text-xs font-medium text-foreground-secondary">
            {{ t("backupTasks.form.priority") }}
          </dt>
          <dd class="mt-1 text-sm font-medium text-foreground">
            {{ task.priority || "-" }}
          </dd>
        </div>
        <div class="rounded-lg border border-border bg-background/50 p-3">
          <dt class="text-xs font-medium text-foreground-secondary">
            {{ t("backupTasks.detail.createdUpdated") }}
          </dt>
          <dd class="mt-1 text-sm font-medium text-foreground">
            {{ formatDateTime(task.created_at) }} /
            {{ formatDateTime(task.updated_at) }}
          </dd>
        </div>
      </dl>
    </section>

    <div class="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <section class="rounded-xl border border-border bg-card p-4 shadow-sm">
        <div class="mb-4 flex items-start gap-3">
          <span
            class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-300"
          >
            <FolderIcon class="h-5 w-5" />
          </span>
          <div>
            <h3 class="font-semibold text-foreground">
              {{ t("backupTasks.backupSource") }}
            </h3>
            <p class="mt-0.5 text-xs text-foreground-secondary">
              {{ source?.name || "-" }}
            </p>
          </div>
        </div>
        <div class="grid grid-cols-1 gap-3 text-sm md:grid-cols-2">
          <div
            v-for="[label, value] in sourceRows"
            :key="label"
            class="rounded-lg border border-border bg-background/50 p-3"
          >
            <p class="text-xs font-medium text-foreground-secondary">
              {{ label }}
            </p>
            <p class="mt-1 break-all text-sm font-medium text-foreground">
              {{ value }}
            </p>
          </div>
        </div>
        <div class="mt-4 rounded-lg border border-border bg-background/50 p-3">
          <p class="mb-2 text-xs font-medium text-foreground-secondary">
            {{ t("backupTasks.form.sourcePaths") }}
          </p>
          <div class="space-y-1.5">
            <p
              v-for="(path, i) in task.backup_paths || []"
              :key="i"
              class="rounded-md border border-border bg-background-secondary px-2.5 py-1.5 font-mono text-xs text-foreground"
            >
              {{ path }}
            </p>
            <p
              v-if="!task.backup_paths?.length"
              class="text-sm text-foreground-muted"
            >
              -
            </p>
          </div>
        </div>
      </section>

      <section class="rounded-xl border border-border bg-card p-4 shadow-sm">
        <div class="mb-4 flex items-start gap-3">
          <span
            class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-sky-500/10 text-sky-600 dark:text-sky-300"
          >
            <ServerStackIcon class="h-5 w-5" />
          </span>
          <div>
            <h3 class="font-semibold text-foreground">
              {{ t("backupTasks.backupRepository") }}
            </h3>
            <p class="mt-0.5 text-xs text-foreground-secondary">
              {{ repository?.name || "-" }}
            </p>
          </div>
        </div>
        <div class="grid grid-cols-1 gap-3 text-sm md:grid-cols-2">
          <div
            v-for="[label, value] in repositoryRows"
            :key="label"
            class="rounded-lg border border-border bg-background/50 p-3"
          >
            <p class="text-xs font-medium text-foreground-secondary">
              {{ label }}
            </p>
            <p class="mt-1 break-all text-sm font-medium text-foreground">
              {{ value }}
            </p>
          </div>
        </div>
      </section>
    </div>

    <section class="rounded-xl border border-border bg-card p-4 shadow-sm">
      <div class="mb-4 flex items-start gap-3">
        <span
          class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-violet-500/10 text-violet-600 dark:text-violet-300"
        >
          <FolderIcon class="h-5 w-5" />
        </span>
        <div>
          <h3 class="font-semibold text-foreground">
            {{ t("backupTasks.detail.pathsAndFilters") }}
          </h3>
          <p class="mt-0.5 text-xs text-foreground-secondary">
            {{ t("backupTasks.form.excludePaths") }}
          </p>
        </div>
      </div>
      <div class="rounded-lg border border-border bg-background/50 p-3">
        <p class="mb-2 text-xs font-medium text-foreground-secondary">
          {{ t("backupTasks.files.exclusionPatterns") }}
        </p>
        <div class="flex flex-wrap gap-2">
          <span
            v-for="(pattern, i) in task.exclude_patterns || []"
            :key="i"
            class="rounded-md border border-border bg-background-secondary px-2.5 py-1 text-xs font-medium text-foreground"
          >
            {{ pattern }}
          </span>
          <span
            v-if="!task.exclude_patterns?.length"
            class="text-sm text-foreground-muted"
          >
            -
          </span>
        </div>
      </div>
    </section>

    <section class="rounded-xl border border-border bg-card p-4 shadow-sm">
      <div class="mb-4 flex items-start gap-3">
        <span
          class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-300"
        >
          <ClockIcon class="h-5 w-5" />
        </span>
        <div>
          <h3 class="font-semibold text-foreground">
            {{ t("backupTasks.detail.scheduleRetention") }}
          </h3>
          <p class="mt-0.5 text-xs text-foreground-secondary">
            {{ task.schedule_name || t("backupTasks.form.noPolicy") }}
          </p>
        </div>
      </div>
      <dl class="grid grid-cols-1 gap-3 text-sm md:grid-cols-3">
        <div class="rounded-lg border border-border bg-background/50 p-3">
          <dt class="text-xs font-medium text-foreground-secondary">
            {{ t("backupTasks.form.policy") }}
          </dt>
          <dd class="mt-1 text-sm font-medium text-foreground">
            {{ task.schedule_name || t("backupTasks.form.noPolicy") }}
          </dd>
        </div>
        <div class="rounded-lg border border-border bg-background/50 p-3">
          <dt class="text-xs font-medium text-foreground-secondary">
            {{ t("backupTasks.nextBackup") }}
          </dt>
          <dd class="mt-1 text-sm font-medium text-foreground">
            {{ formatDateTime(task.next_run_time) }}
          </dd>
        </div>
        <div class="rounded-lg border border-border bg-background/50 p-3">
          <dt class="text-xs font-medium text-foreground-secondary">
            {{ t("backupTasks.lastBackup") }}
          </dt>
          <dd class="mt-1 text-sm font-medium text-foreground">
            {{ formatDateTime(task.last_run_time || task.completed_at) }}
          </dd>
        </div>
        <div class="rounded-lg border border-border bg-background/50 p-3">
          <dt class="text-xs font-medium text-foreground-secondary">
            {{ t("backupTasks.form.retentionDays") }}
          </dt>
          <dd class="mt-1 text-sm font-medium text-foreground">
            {{ task.retention_days || "-" }}
          </dd>
        </div>
        <div class="rounded-lg border border-border bg-background/50 p-3">
          <dt class="text-xs font-medium text-foreground-secondary">
            {{ t("backupTasks.form.maxSnapshots") }}
          </dt>
          <dd class="mt-1 text-sm font-medium text-foreground">
            {{ task.max_snapshots || "-" }}
          </dd>
        </div>
        <div class="rounded-lg border border-border bg-background/50 p-3">
          <dt class="text-xs font-medium text-foreground-secondary">
            {{ t("backupTasks.detail.retries") }}
          </dt>
          <dd class="mt-1 text-sm font-medium text-foreground">
            {{ task.retry_count || 0 }} / {{ task.max_retries || 0 }}
          </dd>
        </div>
      </dl>
    </section>

    <section class="rounded-xl border border-border bg-card p-4 shadow-sm">
      <div class="mb-4 flex items-start gap-3">
        <span
          class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-300"
        >
          <ShieldCheckIcon class="h-5 w-5" />
        </span>
        <div>
          <h3 class="font-semibold text-foreground">
            {{ t("backupTasks.detail.securityCompression") }}
          </h3>
          <p class="mt-0.5 text-xs text-foreground-secondary">
            {{
              task.compression_enabled
                ? task.compression_type || "-"
                : t("common.no")
            }}
          </p>
        </div>
      </div>
      <dl class="grid grid-cols-1 gap-3 text-sm md:grid-cols-3">
        <div class="rounded-lg border border-border bg-background/50 p-3">
          <dt class="text-xs font-medium text-foreground-secondary">
            {{ t("backupTasks.detail.encryption") }}
          </dt>
          <dd class="mt-1 text-sm font-medium text-foreground">
            {{ task.encryption_enabled ? t("common.yes") : t("common.no") }}
          </dd>
        </div>
        <div class="rounded-lg border border-border bg-background/50 p-3">
          <dt class="text-xs font-medium text-foreground-secondary">
            {{ t("backupTasks.detail.checksum") }}
          </dt>
          <dd class="mt-1 text-sm font-medium text-foreground">
            {{ task.verify_checksum ? t("common.yes") : t("common.no") }}
          </dd>
        </div>
        <div class="rounded-lg border border-border bg-background/50 p-3">
          <dt class="text-xs font-medium text-foreground-secondary">
            {{ t("backupTasks.detail.compression") }}
          </dt>
          <dd class="mt-1 text-sm font-medium text-foreground">
            {{
              task.compression_enabled
                ? task.compression_type || "-"
                : t("common.no")
            }}
          </dd>
        </div>
        <div class="rounded-lg border border-border bg-background/50 p-3">
          <dt class="text-xs font-medium text-foreground-secondary">
            {{ t("backupTasks.detail.compressionLevel") }}
          </dt>
          <dd class="mt-1 text-sm font-medium text-foreground">
            {{ task.compression_level ?? "-" }}
          </dd>
        </div>
        <div class="rounded-lg border border-border bg-background/50 p-3">
          <dt class="text-xs font-medium text-foreground-secondary">
            {{ t("backupTasks.detail.checkpoint") }}
          </dt>
          <dd class="mt-1 text-sm font-medium text-foreground">
            {{
              task.enable_checkpoint
                ? `${task.checkpoint_interval_minutes || "-"}m`
                : t("common.no")
            }}
          </dd>
        </div>
        <div class="rounded-lg border border-border bg-background/50 p-3">
          <dt class="text-xs font-medium text-foreground-secondary">
            {{ t("backupTasks.detail.concurrency") }}
          </dt>
          <dd class="mt-1 text-sm font-medium text-foreground">
            {{ task.max_concurrent_files || "-" }}
          </dd>
        </div>
      </dl>
    </section>

    <section class="rounded-xl border border-border bg-card p-4 shadow-sm">
      <div class="mb-4 flex items-start gap-3">
        <span
          class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"
        >
          <BoltIcon class="h-5 w-5" />
        </span>
        <div>
          <h3 class="font-semibold text-foreground">
            {{ t("backupTasks.detail.observability") }}
          </h3>
          <p class="mt-0.5 text-xs text-foreground-secondary">
            {{ task.progress || 0 }}%
          </p>
        </div>
      </div>
      <div class="mb-4 rounded-lg border border-border bg-background/50 p-3">
        <div class="mb-2 flex items-center justify-between text-xs">
          <span class="font-medium text-foreground-secondary">
            {{ t("backupTasks.progress.progress") }}
          </span>
          <span class="font-semibold text-foreground">
            {{ task.progress || 0 }}%
          </span>
        </div>
        <div class="h-2 overflow-hidden rounded-full bg-background-secondary">
          <div
            class="h-full rounded-full bg-primary transition-all"
            :style="{
              width: `${Math.min(Math.max(task.progress || 0, 0), 100)}%`,
            }"
          />
        </div>
      </div>
      <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
        <div class="rounded-lg border border-border bg-background/50 p-3">
          <p class="text-xs font-medium text-foreground-secondary">
            {{ t("backupTasks.progress.files") }}
          </p>
          <p class="mt-1 text-lg font-semibold text-foreground">
            {{ task.backed_up_files || 0 }} / {{ task.total_files || 0 }}
          </p>
        </div>
        <div class="rounded-lg border border-border bg-background/50 p-3">
          <p class="text-xs font-medium text-foreground-secondary">
            {{ t("backupTasks.progress.size") }}
          </p>
          <p class="mt-1 text-lg font-semibold text-foreground">
            {{ formatBytes(task.backed_up_size || 0) }} /
            {{ formatBytes(task.total_size || 0) }}
          </p>
        </div>
        <div class="rounded-lg border border-border bg-background/50 p-3">
          <p class="text-xs font-medium text-foreground-secondary">
            {{ t("backupTasks.progress.speed") }}
          </p>
          <p class="mt-1 text-lg font-semibold text-foreground">
            {{ formatSpeed(task.bytes_per_second) }}
          </p>
        </div>
        <div class="rounded-lg border border-border bg-background/50 p-3">
          <p class="text-xs font-medium text-foreground-secondary">
            {{ t("backupTasks.detail.retries") }}
          </p>
          <p class="mt-1 text-lg font-semibold text-foreground">
            {{ task.retry_count || 0 }} / {{ task.max_retries || 0 }}
          </p>
        </div>
      </div>
    </section>
  </div>
</template>
