<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  CloudArrowUpIcon,
  FolderIcon,
  ServerStackIcon,
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
}>();

const { t } = useI18n();
</script>

<template>
  <div class="rounded-lg border border-border bg-background-secondary p-4">
    <div class="mb-4 flex items-center gap-2">
      <CloudArrowUpIcon class="h-5 w-5 text-primary" />
      <h3 class="font-semibold text-foreground">
        {{ t("backupTasks.edit.sections.readonly") }}
      </h3>
    </div>
    <p class="mb-4 text-xs text-foreground-secondary">
      {{ t("backupTasks.edit.sections.readonlyDesc") }}
    </p>
    <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <div class="rounded-lg border border-border bg-card p-3">
        <div class="mb-3 flex items-center gap-2">
          <FolderIcon class="h-4 w-4 text-primary" />
          <div>
            <p class="text-sm font-semibold text-foreground">
              {{ t("backupTasks.backupSource") }}
            </p>
            <p class="text-xs text-foreground-muted">
              {{ source?.name || task.source_resource_name || "-" }}
            </p>
          </div>
        </div>
        <div class="grid grid-cols-1 gap-2 md:grid-cols-2">
          <div
            v-for="[label, value] in sourceRows"
            :key="label"
            class="rounded-md border border-border bg-background/60 p-2"
          >
            <p class="text-xs text-foreground-secondary">
              {{ label }}
            </p>
            <p class="mt-0.5 break-all text-sm font-medium text-foreground">
              {{ value }}
            </p>
          </div>
        </div>
        <div class="mt-3 rounded-md border border-border bg-background/60 p-2">
          <p class="text-xs text-foreground-secondary">
            {{ t("backupTasks.form.sourcePaths") }}
          </p>
          <div v-if="task.backup_paths?.length" class="mt-1 space-y-1.5">
            <p
              v-for="(path, index) in task.backup_paths"
              :key="index"
              class="rounded-md border border-border bg-background px-2 py-1.5 font-mono text-xs text-foreground"
            >
              {{ path }}
            </p>
          </div>
          <p v-else class="mt-1 text-sm text-foreground-muted">-</p>
        </div>
      </div>
      <div class="rounded-lg border border-border bg-card p-3">
        <div class="mb-3 flex items-center gap-2">
          <ServerStackIcon class="h-4 w-4 text-primary" />
          <div>
            <p class="text-sm font-semibold text-foreground">
              {{ t("backupTasks.backupRepository") }}
            </p>
            <p class="text-xs text-foreground-muted">
              {{ repository?.name || task.target_repository_name || "-" }}
            </p>
          </div>
        </div>
        <div class="grid grid-cols-1 gap-2 md:grid-cols-2">
          <div
            v-for="[label, value] in repositoryRows"
            :key="label"
            class="rounded-md border border-border bg-background/60 p-2"
          >
            <p class="text-xs text-foreground-secondary">
              {{ label }}
            </p>
            <p class="mt-0.5 break-all text-sm font-medium text-foreground">
              {{ value }}
            </p>
          </div>
        </div>
      </div>
    </div>
    <p class="mt-3 text-xs text-foreground-secondary">
      {{ t("backupTasks.edit.readonlyHint") }}
    </p>
  </div>
</template>
