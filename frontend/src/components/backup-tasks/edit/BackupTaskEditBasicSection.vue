<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { DocumentIcon } from "@heroicons/vue/24/outline";

const form = defineModel<any>("form", { required: true });
const { t } = useI18n();
</script>

<template>
  <section class="rounded-lg border border-border bg-card p-4">
    <div class="mb-2 flex items-center gap-2">
      <DocumentIcon class="h-5 w-5 text-primary" />
      <h3 class="font-semibold text-foreground">
        {{ t("backupTasks.detail.basic") }}
      </h3>
    </div>
    <p class="mb-4 text-xs text-foreground-secondary">
      {{ t("backupTasks.edit.sections.basicDesc") }}
    </p>
    <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
      <div>
        <label class="block text-sm font-medium text-foreground mb-1">
          {{ t("backupTasks.form.taskName") }}
        </label>
        <input
          v-model="form.name"
          type="text"
          :placeholder="t('backupTasks.edit.placeholders.name')"
          class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          required
        />
        <p class="mt-1 text-xs text-foreground-muted">
          {{ t("backupTasks.edit.fieldDescriptions.name") }}
        </p>
      </div>
      <div>
        <label class="block text-sm font-medium text-foreground mb-1">
          {{ t("backupTasks.form.priority") }}
        </label>
        <select
          v-model="form.priority"
          class="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        >
          <option value="low">Low</option>
          <option value="normal">Normal</option>
          <option value="high">High</option>
        </select>
        <p class="mt-1 text-xs text-foreground-muted">
          {{ t("backupTasks.edit.fieldDescriptions.priority") }}
        </p>
      </div>
      <div class="md:col-span-2">
        <label class="block text-sm font-medium text-foreground mb-1">
          {{ t("common.description") }}
        </label>
        <textarea
          v-model="form.description"
          rows="3"
          :placeholder="t('backupTasks.edit.placeholders.description')"
          class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        />
        <p class="mt-1 text-xs text-foreground-muted">
          {{ t("backupTasks.edit.fieldDescriptions.description") }}
        </p>
      </div>
      <label
        class="flex items-start gap-3 rounded-lg border border-border bg-background/50 p-3 text-sm text-foreground md:col-span-2"
      >
        <input
          v-model="form.is_enabled"
          type="checkbox"
          class="mt-1 h-4 w-4 rounded border-border text-primary focus:ring-primary"
        />
        <span>
          <span class="font-medium">{{ t("backupTasks.enabled") }}</span>
          <span class="mt-1 block text-xs leading-5 text-foreground-muted">
            {{ t("backupTasks.edit.fieldDescriptions.enabled") }}
          </span>
        </span>
      </label>
    </div>
  </section>
</template>
