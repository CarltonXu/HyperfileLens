<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { CircleStackIcon } from "@heroicons/vue/24/outline";
import {
  isNoChangeSnapshotReference,
  isSnapshotBrowsable,
  snapshotCardClass,
  snapshotDisplayFileCount,
  snapshotDisplaySize,
  snapshotDisplayTime,
  snapshotStatusClass,
} from "@/features/backup-tasks/snapshotDisplay";

const props = defineProps<{
  snapshots: any[];
  selectedSnapshotId?: string | number;
  latestSnapshotId?: string | number;
  formatCompactDateTime: (value?: string | null) => string;
  formatBytes: (value: number) => string;
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
  <div class="grid grid-cols-[repeat(auto-fill,minmax(108px,1fr))] gap-2.5">
    <button
      v-for="snapshot in props.snapshots"
      :key="snapshot.id"
      type="button"
      :disabled="!isSnapshotBrowsable(snapshot)"
      :class="[
        'group relative aspect-square overflow-visible rounded-lg border p-2.5 text-left transition-all focus:outline-none focus:ring-2 focus:ring-primary',
        snapshotCardClass(snapshot, props.selectedSnapshotId),
      ]"
      @click="$emit('select', snapshot)"
      @mouseenter="$emit('hover', snapshot, $event)"
      @mouseleave="$emit('hideHover')"
      @focus="$emit('hover', snapshot, $event)"
      @blur="$emit('hideHover')"
    >
      <span
        v-if="isNoChangeSnapshotReference(snapshot)"
        :title="t('backupTasks.detail.noChanges')"
        class="absolute left-2 top-2 h-2.5 w-2.5 rounded-full bg-amber-500 ring-2 ring-card dark:ring-background"
      />
      <div class="flex items-center justify-between gap-2">
        <span
          :class="[
            'inline-flex h-7 w-7 items-center justify-center rounded-md',
            !isSnapshotBrowsable(snapshot)
              ? 'bg-slate-200 text-slate-500 dark:bg-slate-800 dark:text-slate-400'
              : props.selectedSnapshotId === snapshot.id
              ? 'bg-emerald-600 text-white'
              : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
          ]"
        >
          <CircleStackIcon class="w-4 h-4" />
        </span>
        <span
          v-if="props.latestSnapshotId === snapshot.id"
          class="rounded-full bg-emerald-600 px-1.5 py-0.5 text-[10px] font-medium text-white"
        >
          {{ t("backupTasks.detail.latest") }}
        </span>
      </div>
      <p class="mt-2 truncate text-xs font-medium text-foreground">
        {{ props.formatCompactDateTime(snapshotDisplayTime(snapshot)) }}
      </p>
      <p class="mt-1 truncate text-[11px] text-foreground-secondary">
        {{ props.formatBytes(snapshotDisplaySize(snapshot)) }}
      </p>
      <span
        :class="[
          'mt-1 inline-flex max-w-full rounded-full px-1.5 py-0.5 text-[10px] font-medium',
          snapshotStatusClass(snapshot),
        ]"
      >
        {{ snapshotStatusLabel(snapshot) }}
      </span>
      <div class="mt-2 flex items-center justify-between text-[11px]">
        <span class="text-foreground-muted">
          {{
            isNoChangeSnapshotReference(snapshot)
              ? t("backupTasks.detail.changedFiles", { count: 0 })
              : `${snapshotDisplayFileCount(snapshot)} ${t(
                  "backupTasks.progress.files",
                )}`
          }}
        </span>
        <span
          v-if="
            props.selectedSnapshotId === snapshot.id &&
            isSnapshotBrowsable(snapshot)
          "
          class="h-2 w-2 rounded-full bg-emerald-500"
        />
      </div>
    </button>
  </div>
</template>
