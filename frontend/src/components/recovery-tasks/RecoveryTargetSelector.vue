<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { ServerIcon } from "@heroicons/vue/24/outline";
import type { ProxyNode } from "@/types/proxy";
import type { RecoveryType } from "@/types/recovery";

const props = defineProps<{
  nodes: ProxyNode[];
  selectedNode: string | number;
  recoveryType: RecoveryType;
  targetPath: string;
}>();

const emit = defineEmits<{
  "update:selectedNode": [value: string | number];
  "update:recoveryType": [value: RecoveryType];
  "update:targetPath": [value: string];
}>();

const { t } = useI18n();
</script>

<template>
  <section class="rounded-lg border border-border bg-background-secondary/40 p-4">
    <div class="flex items-start gap-3 mb-4">
      <ServerIcon class="w-5 h-5 text-emerald-600 mt-0.5" />
      <div>
        <h3 class="text-sm font-semibold text-foreground">
          {{ t("recoveryTasks.sections.target") }}
        </h3>
        <p class="text-xs text-foreground-secondary mt-1">
          {{ t("recoveryTasks.sections.targetHelp") }}
        </p>
      </div>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div>
        <label class="block text-sm font-medium text-foreground-secondary mb-1">
          {{ t("recoveryTasks.form.targetNode") }}
        </label>
        <select
          :value="props.selectedNode"
          class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500"
          @change="
            emit('update:selectedNode', ($event.target as HTMLSelectElement).value)
          "
        >
          <option class="bg-background" value="">
            {{ t("common.select") || "Select" }}
          </option>
          <option
            v-for="node in props.nodes"
            :key="node.id"
            class="bg-background"
            :value="node.id"
          >
            {{ node.name }} · {{ node.status }}
          </option>
        </select>
      </div>
      <div>
        <label class="block text-sm font-medium text-foreground-secondary mb-1">
          {{ t("recoveryTasks.form.type") }}
        </label>
        <select
          :value="props.recoveryType"
          class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500"
          @change="
            emit(
              'update:recoveryType',
              ($event.target as HTMLSelectElement).value as RecoveryType,
            )
          "
        >
          <option class="bg-background" value="new_location">
            {{ t("recoveryTasks.types.new_location") }}
          </option>
          <option class="bg-background" value="original">
            {{ t("recoveryTasks.types.original") }}
          </option>
        </select>
      </div>
    </div>
    <div class="mt-4">
      <label class="block text-sm font-medium text-foreground-secondary mb-1">
        {{ t("recoveryTasks.form.targetPath") }}
      </label>
      <input
        :value="props.targetPath"
        type="text"
        :placeholder="t('recoveryTasks.form.targetPathPlaceholder')"
        class="w-full px-3 py-2 font-mono text-sm border border-border rounded-lg bg-background text-foreground placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
        @input="
          emit('update:targetPath', ($event.target as HTMLInputElement).value)
        "
      />
      <p class="text-xs text-foreground-secondary mt-1">
        {{ t("recoveryTasks.form.targetPathHelp") }}
      </p>
    </div>
  </section>
</template>
