<script setup lang="ts">
import {
  ArrowPathIcon,
  QuestionMarkCircleIcon,
} from "@heroicons/vue/24/outline";
import { useI18n } from "vue-i18n";

type SnapshotViewMode = "grid" | "timeline" | "blocks";
type SnapshotGroupBy = "all" | "day" | "month" | "change" | "size";

type Option<T extends string> = {
  value: T;
  label: string;
};

const props = defineProps<{
  collapseNoChangeSnapshots: boolean;
  hiddenNoChangeSnapshotCount: number;
  snapshotOperationLoading: boolean;
  viewMode: SnapshotViewMode;
  viewModeOptions: Option<SnapshotViewMode>[];
  groupBy: SnapshotGroupBy;
  groupOptions: Option<SnapshotGroupBy>[];
}>();

defineEmits<{
  "update:collapseNoChangeSnapshots": [value: boolean];
  "update:viewMode": [value: SnapshotViewMode];
  "update:groupBy": [value: SnapshotGroupBy];
  help: [event: MouseEvent | FocusEvent, key: string];
  hideHelp: [];
  sync: [];
  applyRetention: [];
  runMaintenance: [];
}>();

const { t } = useI18n();
</script>

<template>
  <div class="flex flex-wrap items-center justify-between gap-3">
    <div
      class="inline-flex items-center gap-2 rounded-full border border-border bg-card px-2.5 py-1.5 text-xs font-medium text-foreground shadow-sm"
    >
      <button
        type="button"
        role="switch"
        :aria-checked="props.collapseNoChangeSnapshots"
        class="inline-flex items-center gap-2 transition-colors hover:text-primary focus:outline-none"
        @click="
          $emit(
            'update:collapseNoChangeSnapshots',
            !props.collapseNoChangeSnapshots,
          )
        "
      >
        <span
          :class="[
            'relative inline-flex h-5 w-9 items-center rounded-full transition-colors',
            props.collapseNoChangeSnapshots
              ? 'bg-primary'
              : 'bg-background-tertiary',
          ]"
        >
          <span
            :class="[
              'inline-block h-4 w-4 rounded-full bg-white shadow transition-transform',
              props.collapseNoChangeSnapshots
                ? 'translate-x-4'
                : 'translate-x-0.5',
            ]"
          />
        </span>
        <span>{{ t("backupTasks.detail.collapseNoChanges") }}</span>
      </button>
      <button
        type="button"
        class="inline-flex h-5 w-5 items-center justify-center rounded-full text-foreground-muted transition-colors hover:bg-background-secondary hover:text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
        @mouseenter="
          $emit('help', $event, 'backupTasks.detail.collapseNoChangesHelp')
        "
        @mouseleave="$emit('hideHelp')"
        @focus="
          $emit('help', $event, 'backupTasks.detail.collapseNoChangesHelp')
        "
        @blur="$emit('hideHelp')"
        @click.stop
      >
        <QuestionMarkCircleIcon class="h-4 w-4" />
      </button>
      <span
        v-if="props.hiddenNoChangeSnapshotCount > 0"
        class="rounded-full bg-background-secondary px-1.5 py-0.5 text-[11px] text-foreground-secondary"
      >
        {{ props.hiddenNoChangeSnapshotCount }}
      </span>
    </div>

    <div class="flex flex-wrap items-center justify-end gap-2">
      <div
        class="inline-flex flex-wrap items-center gap-1 rounded-lg border border-border bg-card p-1 text-xs shadow-sm"
      >
        <button
          type="button"
          class="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 font-medium text-foreground-secondary transition-colors hover:bg-hover hover:text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-60"
          :disabled="props.snapshotOperationLoading"
          @mouseenter="
            $emit('help', $event, 'backupTasks.detail.syncSnapshotsHelp')
          "
          @mouseleave="$emit('hideHelp')"
          @focus="$emit('help', $event, 'backupTasks.detail.syncSnapshotsHelp')"
          @blur="$emit('hideHelp')"
          @click="$emit('sync')"
        >
          <ArrowPathIcon
            :class="[
              'h-3.5 w-3.5',
              props.snapshotOperationLoading ? 'animate-spin' : '',
            ]"
          />
          {{ t("backupTasks.detail.syncSnapshots") }}
          <QuestionMarkCircleIcon class="h-3.5 w-3.5 text-foreground-muted" />
        </button>
        <button
          type="button"
          class="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 font-medium text-foreground-secondary transition-colors hover:bg-hover hover:text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-60"
          :disabled="props.snapshotOperationLoading"
          @mouseenter="
            $emit('help', $event, 'backupTasks.detail.applyRetentionHelp')
          "
          @mouseleave="$emit('hideHelp')"
          @focus="
            $emit('help', $event, 'backupTasks.detail.applyRetentionHelp')
          "
          @blur="$emit('hideHelp')"
          @click="$emit('applyRetention')"
        >
          {{ t("backupTasks.detail.applyRetention") }}
          <QuestionMarkCircleIcon class="h-3.5 w-3.5 text-foreground-muted" />
        </button>
        <button
          type="button"
          class="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 font-medium text-foreground-secondary transition-colors hover:bg-hover hover:text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-60"
          :disabled="props.snapshotOperationLoading"
          @mouseenter="
            $emit('help', $event, 'backupTasks.detail.runMaintenanceHelp')
          "
          @mouseleave="$emit('hideHelp')"
          @focus="
            $emit('help', $event, 'backupTasks.detail.runMaintenanceHelp')
          "
          @blur="$emit('hideHelp')"
          @click="$emit('runMaintenance')"
        >
          {{ t("backupTasks.detail.runMaintenance") }}
          <QuestionMarkCircleIcon class="h-3.5 w-3.5 text-foreground-muted" />
        </button>
      </div>

      <div
        class="inline-flex flex-wrap items-center gap-1 rounded-lg border border-border bg-card p-1 text-xs shadow-sm"
      >
        <button
          v-for="option in props.viewModeOptions"
          :key="option.value"
          type="button"
          :class="[
            'rounded-md px-2.5 py-1.5 font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-primary',
            props.viewMode === option.value
              ? 'bg-primary text-white shadow-sm'
              : 'text-foreground-secondary hover:bg-hover hover:text-foreground',
          ]"
          @click="$emit('update:viewMode', option.value)"
        >
          {{ option.label }}
        </button>
      </div>

      <div
        class="inline-flex flex-wrap items-center gap-1 rounded-lg border border-border bg-card p-1 text-xs shadow-sm"
      >
        <button
          v-for="option in props.groupOptions"
          :key="option.value"
          type="button"
          :class="[
            'rounded-md px-2.5 py-1.5 font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-primary',
            props.groupBy === option.value
              ? 'bg-primary text-white shadow-sm'
              : 'text-foreground-secondary hover:bg-hover hover:text-foreground',
          ]"
          @click="$emit('update:groupBy', option.value)"
        >
          {{ option.label }}
        </button>
      </div>
    </div>
  </div>
</template>
