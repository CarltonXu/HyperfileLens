<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { ShieldCheckIcon } from "@heroicons/vue/24/outline";

const form = defineModel<any>("form", { required: true });
const { t } = useI18n();
</script>

<template>
  <section class="rounded-lg border border-border bg-card p-4">
    <div class="mb-2 flex items-center gap-2">
      <ShieldCheckIcon class="h-5 w-5 text-primary" />
      <h3 class="font-semibold text-foreground">
        {{ t("backupTasks.detail.securityCompression") }}
      </h3>
    </div>
    <p class="mb-4 text-xs text-foreground-secondary">
      {{ t("backupTasks.edit.sections.securityDesc") }}
    </p>
    <div class="grid grid-cols-1 gap-4 md:grid-cols-4">
      <label
        class="flex items-start gap-3 rounded-lg border border-border bg-background/50 p-3 text-sm text-foreground"
      >
        <input
          v-model="form.encryption_enabled"
          type="checkbox"
          class="mt-1 h-4 w-4 rounded border-border text-primary focus:ring-primary"
        />
        <span>
          <span class="font-medium">{{
            t("backupTasks.detail.encryption")
          }}</span>
          <span class="mt-1 block text-xs leading-5 text-foreground-muted">
            {{ t("backupTasks.edit.fieldDescriptions.encryption") }}
          </span>
        </span>
      </label>
      <label
        class="flex items-start gap-3 rounded-lg border border-border bg-background/50 p-3 text-sm text-foreground"
      >
        <input
          v-model="form.verify_checksum"
          type="checkbox"
          class="mt-1 h-4 w-4 rounded border-border text-primary focus:ring-primary"
        />
        <span>
          <span class="font-medium">{{
            t("backupTasks.detail.checksum")
          }}</span>
          <span class="mt-1 block text-xs leading-5 text-foreground-muted">
            {{ t("backupTasks.edit.fieldDescriptions.checksum") }}
          </span>
        </span>
      </label>
      <label
        class="flex items-start gap-3 rounded-lg border border-border bg-background/50 p-3 text-sm text-foreground"
      >
        <input
          v-model="form.compression_enabled"
          type="checkbox"
          class="mt-1 h-4 w-4 rounded border-border text-primary focus:ring-primary"
        />
        <span>
          <span class="font-medium">{{
            t("backupTasks.detail.compression")
          }}</span>
          <span class="mt-1 block text-xs leading-5 text-foreground-muted">
            {{ t("backupTasks.edit.fieldDescriptions.compression") }}
          </span>
        </span>
      </label>
      <label
        class="flex items-start gap-3 rounded-lg border border-border bg-background/50 p-3 text-sm text-foreground"
      >
        <input
          v-model="form.enable_checkpoint"
          type="checkbox"
          class="mt-1 h-4 w-4 rounded border-border text-primary focus:ring-primary"
        />
        <span>
          <span class="font-medium">{{
            t("backupTasks.detail.checkpoint")
          }}</span>
          <span class="mt-1 block text-xs leading-5 text-foreground-muted">
            {{ t("backupTasks.edit.fieldDescriptions.checkpoint") }}
          </span>
        </span>
      </label>
      <div>
        <label class="block text-sm font-medium text-foreground mb-1">
          {{ t("backupTasks.detail.compression") }}
        </label>
        <select
          v-model="form.compression_type"
          :disabled="!form.compression_enabled"
          class="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
        >
          <option value="zstd">zstd</option>
          <option value="gzip">gzip</option>
          <option value="none">{{ t("common.none") }}</option>
        </select>
        <p class="mt-1 text-xs text-foreground-muted">
          {{ t("backupTasks.edit.fieldDescriptions.compressionType") }}
        </p>
      </div>
      <div>
        <label class="block text-sm font-medium text-foreground mb-1">
          {{ t("backupTasks.detail.compressionLevel") }}
        </label>
        <input
          v-model.number="form.compression_level"
          type="number"
          min="0"
          max="9"
          :disabled="!form.compression_enabled"
          :placeholder="t('backupTasks.edit.placeholders.compressionLevel')"
          class="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
        />
        <p class="mt-1 text-xs text-foreground-muted">
          {{ t("backupTasks.edit.fieldDescriptions.compressionLevel") }}
        </p>
      </div>
      <div>
        <label class="block text-sm font-medium text-foreground mb-1">
          {{ t("backupTasks.detail.checkpoint") }}
        </label>
        <input
          v-model.number="form.checkpoint_interval_minutes"
          type="number"
          min="1"
          :disabled="!form.enable_checkpoint"
          :placeholder="t('backupTasks.edit.placeholders.checkpointInterval')"
          class="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
        />
        <p class="mt-1 text-xs text-foreground-muted">
          {{ t("backupTasks.edit.fieldDescriptions.checkpointInterval") }}
        </p>
      </div>
      <div>
        <label class="block text-sm font-medium text-foreground mb-1">
          {{ t("backupTasks.detail.concurrency") }}
        </label>
        <input
          v-model.number="form.max_concurrent_files"
          type="number"
          min="1"
          :placeholder="t('backupTasks.edit.placeholders.concurrency')"
          class="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        />
        <p class="mt-1 text-xs text-foreground-muted">
          {{ t("backupTasks.edit.fieldDescriptions.concurrency") }}
        </p>
      </div>
      <div>
        <label class="block text-sm font-medium text-foreground mb-1">
          {{ t("backupTasks.edit.bandwidthLimit") }}
        </label>
        <input
          v-model.number="form.bandwidth_limit_kbps"
          type="number"
          min="0"
          :placeholder="t('backupTasks.edit.placeholders.bandwidthLimit')"
          class="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        />
        <p class="mt-1 text-xs text-foreground-muted">
          {{ t("backupTasks.edit.fieldDescriptions.bandwidthLimit") }}
        </p>
      </div>
      <div>
        <label class="block text-sm font-medium text-foreground mb-1">
          {{ t("backupTasks.detail.retries") }}
        </label>
        <input
          v-model.number="form.max_retries"
          type="number"
          min="0"
          :placeholder="t('backupTasks.edit.placeholders.maxRetries')"
          class="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        />
        <p class="mt-1 text-xs text-foreground-muted">
          {{ t("backupTasks.edit.fieldDescriptions.maxRetries") }}
        </p>
      </div>
    </div>
  </section>
</template>
