<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  isNoChangeSnapshotReference,
  isSnapshotBrowsable,
  snapshotDisplayFileCount,
  snapshotDisplaySize,
  snapshotDisplayTime,
  snapshotStatusClass,
  snapshotTimelineClass,
  snapshotTimelineDotClass,
} from "@/features/backup-tasks/snapshotDisplay";
import SnapshotFileBrowser from "./SnapshotFileBrowser.vue";

const props = defineProps<{
  snapshots: any[];
  selectedSnapshot: any | null;
  latestSnapshotId?: string | number;
  files: any[];
  visibleFiles: any[];
  filesLoading: boolean;
  filesError: string;
  expandedPaths: Set<string>;
  selectedPaths: Set<string>;
  loadingPaths: Set<string>;
  selectionState: (file: any) => "checked" | "partial" | "none";
  formatDateTime: (value?: string | null) => string;
  formatBytes: (value: number) => string;
}>();

defineEmits<{
  select: [snapshot: any];
  hover: [snapshot: any, event: MouseEvent | FocusEvent];
  hideHover: [];
  retry: [];
  toggleDirectory: [file: any];
  toggleSelection: [file: any];
}>();

const { t } = useI18n();

function snapshotStatusLabel(snapshot: any) {
  const status = snapshot?.snapshot_status || "available";
  return t(`backupTasks.detail.snapshotStatuses.${status}`);
}
</script>

<template>
  <div class="relative space-y-2 pl-6">
    <div class="absolute bottom-3 left-[11px] top-3 w-px bg-border" />
    <div v-for="snapshot in props.snapshots" :key="snapshot.id" class="relative">
      <span
        :class="[
          'absolute -left-[19px] top-4 h-3.5 w-3.5 rounded-full border-2 bg-card',
          snapshotTimelineDotClass(snapshot, props.selectedSnapshot?.id),
        ]"
      />
      <div
        :class="[
          'rounded-lg border bg-card transition-colors',
          snapshotTimelineClass(snapshot, props.selectedSnapshot?.id),
        ]"
      >
        <button
          type="button"
          class="w-full px-3 py-2.5 text-left focus:outline-none focus:ring-2 focus:ring-primary disabled:cursor-not-allowed"
          :disabled="!isSnapshotBrowsable(snapshot)"
          @click="$emit('select', snapshot)"
          @mouseenter="$emit('hover', snapshot, $event)"
          @mouseleave="$emit('hideHover')"
          @focus="$emit('hover', snapshot, $event)"
          @blur="$emit('hideHover')"
        >
          <div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-sm font-semibold text-foreground">
                  {{ props.formatDateTime(snapshotDisplayTime(snapshot)) }}
                </span>
                <span
                  v-if="props.latestSnapshotId === snapshot.id"
                  class="rounded-full bg-emerald-600 px-1.5 py-0.5 text-[10px] font-medium text-white"
                >
                  {{ t("backupTasks.detail.latest") }}
                </span>
                <span
                  v-if="isNoChangeSnapshotReference(snapshot)"
                  class="rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-950/40 dark:text-amber-300"
                >
                  {{ t("backupTasks.detail.noChanges") }}
                </span>
                <span
                  :class="[
                    'rounded-full px-1.5 py-0.5 text-[10px] font-medium',
                    snapshotStatusClass(snapshot),
                  ]"
                >
                  {{ snapshotStatusLabel(snapshot) }}
                </span>
              </div>
              <p class="mt-1 truncate text-xs text-foreground-secondary">
                {{ snapshot.name || snapshot.version || snapshot.id }}
              </p>
            </div>
            <div class="grid grid-cols-3 gap-2 text-right text-xs sm:min-w-[240px]">
              <div>
                <p class="text-foreground-muted">
                  {{ t("backupTasks.progress.size") }}
                </p>
                <p class="font-medium text-foreground">
                  {{ props.formatBytes(snapshotDisplaySize(snapshot)) }}
                </p>
              </div>
              <div>
                <p class="text-foreground-muted">
                  {{ t("backupTasks.progress.files") }}
                </p>
                <p class="font-medium text-foreground">
                  {{
                    isNoChangeSnapshotReference(snapshot)
                      ? 0
                      : snapshotDisplayFileCount(snapshot)
                  }}
                </p>
              </div>
              <div>
                <p class="text-foreground-muted">
                  {{ t("common.status") }}
                </p>
                <p class="font-medium text-foreground">
                  {{
                    isNoChangeSnapshotReference(snapshot)
                      ? t("backupTasks.detail.noChanges")
                      : t("backupTasks.detail.changedSnapshots")
                  }}
                </p>
              </div>
            </div>
          </div>
        </button>
        <div
          v-if="props.selectedSnapshot?.id === snapshot.id"
          class="border-t border-border bg-background/50"
        >
          <div class="px-3 py-2 text-xs text-foreground-secondary">
            {{
              isNoChangeSnapshotReference(props.selectedSnapshot)
                ? t("backupTasks.detail.showingReferencedSnapshot")
                : t("backupTasks.detail.timelineFileBrowserHint")
            }}
          </div>
          <SnapshotFileBrowser
            :selected-snapshot="props.selectedSnapshot"
            :files="props.files"
            :visible-files="props.visibleFiles"
            :loading="props.filesLoading"
            :error="props.filesError"
            :expanded-paths="props.expandedPaths"
            :selected-paths="props.selectedPaths"
            :loading-paths="props.loadingPaths"
            :selection-state="props.selectionState"
            :format-bytes="props.formatBytes"
            compact
            :show-header="false"
            @retry="$emit('retry')"
            @toggle-directory="$emit('toggleDirectory', $event)"
            @toggle-selection="$emit('toggleSelection', $event)"
          />
        </div>
      </div>
    </div>
  </div>
</template>
