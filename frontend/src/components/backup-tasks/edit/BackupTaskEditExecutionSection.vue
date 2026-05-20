<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { ServerStackIcon } from "@heroicons/vue/24/outline";
import type { ProxyNode } from "@/types/proxy";

defineProps<{
  proxies: ProxyNode[];
  canUseAutoPlacement: boolean;
}>();

const form = defineModel<any>("form", { required: true });
const { t } = useI18n();
</script>

<template>
  <section class="rounded-lg border border-border bg-card p-4">
    <div class="mb-2 flex items-center gap-2">
      <ServerStackIcon class="h-5 w-5 text-primary" />
      <h3 class="font-semibold text-foreground">
        {{ t("backupTasks.execution.title") }}
      </h3>
    </div>
    <p class="mb-4 text-xs text-foreground-secondary">
      {{ t("backupTasks.execution.description") }}
    </p>
    <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
      <div>
        <label class="block text-sm font-medium text-foreground mb-1">
          {{ t("backupTasks.execution.title") }}
        </label>
        <select
          v-model="form.execution_mode"
          :disabled="!canUseAutoPlacement"
          class="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-60"
        >
          <option value="pinned">
            {{ t("backupTasks.executionModes.pinned") }}
          </option>
          <option value="preferred">
            {{ t("backupTasks.executionModes.preferred") }}
          </option>
          <option value="auto">
            {{ t("backupTasks.executionModes.auto") }}
          </option>
        </select>
        <p class="mt-1 text-xs text-foreground-muted">
          {{
            canUseAutoPlacement
              ? t("backupTasks.execution.description")
              : t("backupTasks.execution.autoUnavailable")
          }}
        </p>
      </div>
      <div v-if="form.execution_mode === 'preferred'">
        <label class="block text-sm font-medium text-foreground mb-1">
          {{ t("backupTasks.execution.preferredProxy") }}
        </label>
        <select
          v-model="form.preferred_execution_node"
          class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
        >
          <option :value="null">
            {{ t("backupTasks.execution.selectPreferredProxy") }}
          </option>
          <option v-for="node in proxies" :key="node.id" :value="node.id">
            {{ node.name }} · {{ node.status }}
          </option>
        </select>
        <p class="mt-1 text-xs text-foreground-muted">
          {{ t("backupTasks.execution.preferredProxyDesc") }}
        </p>
      </div>
    </div>
  </section>
</template>
