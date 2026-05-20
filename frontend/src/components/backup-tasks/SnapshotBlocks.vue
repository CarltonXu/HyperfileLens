<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  isSnapshotBrowsable,
  snapshotBlockClass,
  snapshotDisplayTime,
} from "@/features/backup-tasks/snapshotDisplay";

const props = defineProps<{
  snapshots: any[];
  selectedSnapshotId?: string | number;
  formatDateTime: (value?: string | null) => string;
}>();

defineEmits<{
  select: [snapshot: any];
  hover: [snapshot: any, event: MouseEvent | FocusEvent];
  hideHover: [];
}>();

const { t } = useI18n();

function snapshotStatusLabel(snapshot: any) {
  const status = snapshot?.snapshot_status || "available";
  return t(`backupTasks.detail.snapshotStatuses.${status}`);
}
</script>

<template>
  <div class="rounded-lg border border-border bg-card p-3">
    <div
      class="mb-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-[11px] text-foreground-secondary"
    >
      <span class="inline-flex items-center gap-1.5">
        <span class="h-2.5 w-2.5 rounded-[3px] bg-emerald-400 dark:bg-emerald-600" />
        {{ t("backupTasks.detail.changedSnapshots") }}
      </span>
      <span class="inline-flex items-center gap-1.5">
        <span class="h-2.5 w-2.5 rounded-[3px] bg-sky-300 dark:bg-sky-600" />
        {{ t("backupTasks.detail.noChangeSnapshots") }}
      </span>
      <span class="inline-flex items-center gap-1.5">
        <span class="h-2.5 w-2.5 rounded-[3px] bg-amber-300 dark:bg-amber-600" />
        {{ t("backupTasks.detail.snapshotStatuses.pending_prune") }}
      </span>
      <span class="inline-flex items-center gap-1.5">
        <span class="h-2.5 w-2.5 rounded-[3px] bg-slate-300 dark:bg-slate-700" />
        {{ t("backupTasks.detail.snapshotStatuses.pruned") }}
      </span>
      <span class="inline-flex items-center gap-1.5">
        <span class="h-2.5 w-2.5 rounded-[3px] bg-red-400 dark:bg-red-700" />
        {{ t("backupTasks.detail.snapshotStatuses.delete_failed") }}
      </span>
    </div>
    <div class="flex flex-wrap content-start gap-1.5">
      <button
        v-for="snapshot in props.snapshots"
        :key="snapshot.id"
        type="button"
        :disabled="!isSnapshotBrowsable(snapshot)"
        :class="[
          'relative h-[18px] w-[18px] rounded-[4px] shadow-sm transition-transform duration-150 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1',
          'disabled:cursor-not-allowed disabled:opacity-45',
          props.selectedSnapshotId === snapshot.id
            ? 'z-10 scale-110'
            : 'hover:z-10 hover:scale-125',
          snapshotBlockClass(snapshot, props.selectedSnapshotId),
        ]"
        :aria-label="`${props.formatDateTime(snapshotDisplayTime(snapshot))} · ${snapshotStatusLabel(snapshot)}`"
        :title="props.formatDateTime(snapshotDisplayTime(snapshot))"
        @click="$emit('select', snapshot)"
        @mouseenter="$emit('hover', snapshot, $event)"
        @mouseleave="$emit('hideHover')"
        @focus="$emit('hover', snapshot, $event)"
        @blur="$emit('hideHover')"
      />
    </div>
  </div>
</template>
