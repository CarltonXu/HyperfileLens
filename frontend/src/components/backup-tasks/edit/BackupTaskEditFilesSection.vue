<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { FolderIcon } from "@heroicons/vue/24/outline";

const form = defineModel<any>("form", { required: true });
const { t } = useI18n();
</script>

<template>
  <section class="rounded-lg border border-border bg-card p-4">
    <div class="mb-2 flex items-center gap-2">
      <FolderIcon class="h-5 w-5 text-primary" />
      <h3 class="font-semibold text-foreground">
        {{ t("backupTasks.files.title") }}
      </h3>
    </div>
    <p class="mb-4 text-xs text-foreground-secondary">
      {{ t("backupTasks.edit.sections.pathsDesc") }}
    </p>
    <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
      <div>
        <label class="block text-sm font-medium text-foreground mb-1">
          {{ t("backupTasks.files.exclusionPatterns") }}
        </label>
        <textarea
          v-model="form.exclude_patterns_text"
          rows="6"
          :placeholder="t('backupTasks.edit.placeholders.excludePatterns')"
          class="w-full font-mono text-sm px-3 py-2 rounded-lg border border-border bg-background text-foreground placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        />
        <p class="mt-1 text-xs text-foreground-muted">
          {{ t("backupTasks.edit.fieldDescriptions.excludePatterns") }}
        </p>
      </div>
      <div>
        <label class="block text-sm font-medium text-foreground mb-1">
          {{ t("backupTasks.files.dotIgnoreFiles") }}
        </label>
        <textarea
          v-model="form.dot_ignore_files_text"
          rows="4"
          placeholder=".kopiaignore"
          class="w-full font-mono text-sm px-3 py-2 rounded-lg border border-border bg-background text-foreground placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        />
        <p class="mt-1 text-xs text-foreground-muted">
          {{ t("backupTasks.files.dotIgnoreFilesDesc") }}
        </p>
      </div>
      <div class="space-y-3">
        <label
          class="flex items-start gap-3 rounded-lg border border-border bg-background/50 p-3 text-sm text-foreground"
        >
          <input
            v-model="form.one_file_system"
            type="checkbox"
            class="mt-1 h-4 w-4 rounded border-border text-primary focus:ring-primary"
          />
          <span>
            <span class="font-medium">
              {{ t("backupTasks.files.oneFileSystem") }}
            </span>
            <span class="mt-1 block text-xs leading-5 text-foreground-muted">
              {{ t("backupTasks.files.oneFileSystemDesc") }}
            </span>
          </span>
        </label>
        <label
          class="flex items-start gap-3 rounded-lg border border-border bg-background/50 p-3 text-sm text-foreground"
        >
          <input
            v-model="form.ignore_file_errors"
            type="checkbox"
            class="mt-1 h-4 w-4 rounded border-border text-primary focus:ring-primary"
          />
          <span>
            <span class="font-medium">
              {{ t("backupTasks.files.ignoreFileErrors") }}
            </span>
            <span class="mt-1 block text-xs leading-5 text-foreground-muted">
              {{ t("backupTasks.files.ignoreFileErrorsDesc") }}
            </span>
          </span>
        </label>
        <label
          class="flex items-start gap-3 rounded-lg border border-border bg-background/50 p-3 text-sm text-foreground"
        >
          <input
            v-model="form.ignore_dir_errors"
            type="checkbox"
            class="mt-1 h-4 w-4 rounded border-border text-primary focus:ring-primary"
          />
          <span>
            <span class="font-medium">
              {{ t("backupTasks.files.ignoreDirErrors") }}
            </span>
            <span class="mt-1 block text-xs leading-5 text-foreground-muted">
              {{ t("backupTasks.files.ignoreDirErrorsDesc") }}
            </span>
          </span>
        </label>
      </div>
    </div>
    <p class="mt-2 text-xs text-foreground-secondary">
      {{ t("backupTasks.edit.onePerLine") }}
    </p>
  </section>
</template>
