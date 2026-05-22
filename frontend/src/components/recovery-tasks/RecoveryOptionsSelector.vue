<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { ShieldCheckIcon } from "@heroicons/vue/24/outline";
import type { ProxyNode } from "@/types/proxy";
import type {
  RecoveryConflictPolicy,
  RecoveryPriority,
  RecoveryTaskCreateData,
  SnapshotInfo,
} from "@/types/recovery";

const props = defineProps<{
  conflictPolicy?: RecoveryConflictPolicy;
  priority?: RecoveryPriority;
  recovery: RecoveryTaskCreateData;
  selectedSnapshot?: SnapshotInfo;
  selectedTargetNode?: ProxyNode;
}>();

const emit = defineEmits<{
  "update:conflictPolicy": [value: RecoveryConflictPolicy];
  "update:priority": [value: RecoveryPriority];
}>();

const { t } = useI18n();
</script>

<template>
  <section class="rounded-lg border border-border bg-background-secondary/40 p-4">
    <div class="flex items-start gap-3 mb-4">
      <ShieldCheckIcon class="w-5 h-5 text-emerald-600 mt-0.5" />
      <div>
        <h3 class="text-sm font-semibold text-foreground">
          {{ t("recoveryTasks.sections.options") }}
        </h3>
        <p class="text-xs text-foreground-secondary mt-1">
          {{ t("recoveryTasks.sections.optionsHelp") }}
        </p>
      </div>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div>
        <label class="block text-sm font-medium text-foreground-secondary mb-1">
          {{ t("recoveryTasks.form.conflictPolicy") }}
        </label>
        <select
          :value="props.conflictPolicy"
          class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500"
          @change="
            emit(
              'update:conflictPolicy',
              ($event.target as HTMLSelectElement).value as RecoveryConflictPolicy,
            )
          "
        >
          <option class="bg-background" value="skip">
            {{ t("recoveryTasks.conflict.skip") }}
          </option>
          <option class="bg-background" value="overwrite">
            {{ t("recoveryTasks.conflict.overwrite") }}
          </option>
        </select>
        <p class="text-xs text-foreground-secondary mt-1">
          {{ t("recoveryTasks.form.conflictHelp") }}
        </p>
      </div>
      <div>
        <label class="block text-sm font-medium text-foreground-secondary mb-1">
          {{ t("recoveryTasks.form.priority") }}
        </label>
        <select
          :value="props.priority"
          class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500"
          @change="
            emit(
              'update:priority',
              ($event.target as HTMLSelectElement).value as RecoveryPriority,
            )
          "
        >
          <option class="bg-background" value="low">Low</option>
          <option class="bg-background" value="normal">Normal</option>
          <option class="bg-background" value="high">High</option>
          <option class="bg-background" value="critical">Critical</option>
        </select>
      </div>
    </div>
    <div class="mt-5 rounded-lg border border-border bg-card p-4">
      <h4 class="text-sm font-semibold text-foreground mb-3">
        {{ t("recoveryTasks.review.title") }}
      </h4>
      <dl class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
        <div>
          <dt class="text-xs text-foreground-secondary">
            {{ t("common.name") }}
          </dt>
          <dd class="font-medium text-foreground mt-1">
            {{ props.recovery.name || "-" }}
          </dd>
        </div>
        <div>
          <dt class="text-xs text-foreground-secondary">
            {{ t("recoveryTasks.form.snapshot") }}
          </dt>
          <dd class="font-medium text-foreground mt-1 break-all">
            {{ props.selectedSnapshot?.name || props.selectedSnapshot?.id || "-" }}
          </dd>
        </div>
        <div>
          <dt class="text-xs text-foreground-secondary">
            {{ t("recoveryTasks.form.targetNode") }}
          </dt>
          <dd class="font-medium text-foreground mt-1">
            {{ props.selectedTargetNode?.name || "-" }}
          </dd>
        </div>
        <div>
          <dt class="text-xs text-foreground-secondary">
            {{ t("recoveryTasks.form.targetPath") }}
          </dt>
          <dd class="font-mono text-xs text-foreground mt-1 break-all">
            {{ props.recovery.target_path || "-" }}
          </dd>
        </div>
      </dl>
    </div>
  </section>
</template>
