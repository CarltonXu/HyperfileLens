<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { CircleStackIcon } from "@heroicons/vue/24/outline";
import Pagination from "@/components/Pagination.vue";
import SnapshotFileBrowser from "./SnapshotFileBrowser.vue";
import SnapshotGroupSection from "./SnapshotGroupSection.vue";
import SnapshotToolbar from "./SnapshotToolbar.vue";
import { isNoChangeSnapshotReference } from "@/features/backup-tasks/snapshotDisplay";

type SnapshotViewMode = "grid" | "timeline" | "blocks";
type SnapshotGroupBy = "all" | "day" | "month" | "change" | "size";

defineProps<{
  loading: boolean;
  allSnapshots: any[];
  displayedSnapshots: any[];
  groups: Array<{
    key: string;
    label: string;
    description: string;
    snapshots: any[];
  }>;
  hiddenNoChangeSnapshotCount: number;
  snapshotOperationLoading: boolean;
  viewModeOptions: Array<{ value: SnapshotViewMode; label: string }>;
  groupOptions: Array<{ value: SnapshotGroupBy; label: string }>;
  selectedSnapshot: any | null;
  files: any[];
  visibleFiles: any[];
  filesLoading: boolean;
  filesError: string;
  expandedPaths: Set<string>;
  selectedPaths: Set<string>;
  loadingPaths: Set<string>;
  selectionState: (file: any) => "checked" | "partial" | "none";
  formatCompactDateTime: (value?: string | null) => string;
  formatDateTime: (value?: string | null) => string;
  formatBytes: (value: number) => string;
  snapshotOperationButtonLoading: boolean;
}>();

const collapseNoChangeSnapshots = defineModel<boolean>(
  "collapseNoChangeSnapshots",
  { required: true },
);
const viewMode = defineModel<SnapshotViewMode>("viewMode", { required: true });
const groupBy = defineModel<SnapshotGroupBy>("groupBy", { required: true });
const currentPage = defineModel<number>("currentPage", { required: true });
const pageSize = defineModel<number>("pageSize", { required: true });

defineEmits<{
  help: [event: MouseEvent | FocusEvent, key: string];
  hideHelp: [];
  sync: [];
  applyRetention: [];
  runMaintenance: [];
  select: [snapshot: any];
  hover: [snapshot: any, event: MouseEvent | FocusEvent];
  hideHover: [];
  retry: [];
  toggleDirectory: [file: any];
  toggleSelection: [file: any];
  clearSelection: [];
  exportSelected: [];
  indexSnapshot: [];
  viewInsights: [];
  analyzeAiInsights: [];
}>();

const { t } = useI18n();
</script>

<template>
  <div class="space-y-4">
    <div v-if="loading" class="py-10 text-center text-foreground-secondary">
      {{ t("common.loading") }}
    </div>
    <div
      v-else-if="allSnapshots.length === 0"
      class="rounded-xl border border-dashed border-border bg-background/50 px-6 py-12 text-center"
    >
      <div
        class="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-50 text-emerald-600 dark:bg-emerald-950/30 dark:text-emerald-300"
      >
        <CircleStackIcon class="h-7 w-7" />
      </div>
      <h3 class="mt-4 text-sm font-semibold text-foreground">
        {{ t("backupTasks.emptyStates.snapshotsTitle") }}
      </h3>
      <p
        class="mx-auto mt-2 max-w-md text-sm leading-6 text-foreground-secondary"
      >
        {{ t("backupTasks.emptyStates.snapshotsDesc") }}
      </p>
    </div>
    <template v-else>
      <SnapshotToolbar
        v-model:collapse-no-change-snapshots="collapseNoChangeSnapshots"
        v-model:view-mode="viewMode"
        v-model:group-by="groupBy"
        :hidden-no-change-snapshot-count="hiddenNoChangeSnapshotCount"
        :snapshot-operation-loading="snapshotOperationLoading"
        :view-mode-options="viewModeOptions"
        :group-options="groupOptions"
        @help="(event, key) => $emit('help', event, key)"
        @hide-help="$emit('hideHelp')"
        @sync="$emit('sync')"
        @apply-retention="$emit('applyRetention')"
        @run-maintenance="$emit('runMaintenance')"
      />
      <div
        v-if="displayedSnapshots.length === 0"
        class="rounded-xl border border-dashed border-border bg-background/50 px-6 py-10 text-center text-sm text-foreground-secondary"
      >
        {{ t("backupTasks.detail.noNormalSnapshots") }}
      </div>
      <div v-else class="space-y-4">
        <SnapshotGroupSection
          v-for="group in groups"
          :key="group.key"
          :group="group"
          :group-by="groupBy"
          :view-mode="viewMode"
          :selected-snapshot="selectedSnapshot"
          :latest-snapshot-id="displayedSnapshots[0]?.id"
          :files="files"
          :visible-files="visibleFiles"
          :files-loading="filesLoading"
          :files-error="filesError"
          :expanded-paths="expandedPaths"
          :selected-paths="selectedPaths"
          :loading-paths="loadingPaths"
          :selection-state="selectionState"
          :format-compact-date-time="formatCompactDateTime"
          :format-date-time="formatDateTime"
          :format-bytes="formatBytes"
          @select="$emit('select', $event)"
          @hover="(snapshot, event) => $emit('hover', snapshot, event)"
          @hide-hover="$emit('hideHover')"
          @retry="$emit('retry')"
          @toggle-directory="$emit('toggleDirectory', $event)"
          @toggle-selection="$emit('toggleSelection', $event)"
        />
        <div class="overflow-hidden rounded-lg border border-border bg-card">
          <Pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :total-items="displayedSnapshots.length"
          />
        </div>

        <SnapshotFileBrowser
          v-if="viewMode === 'grid'"
          :selected-snapshot="selectedSnapshot"
          :files="files"
          :visible-files="visibleFiles"
          :loading="filesLoading"
          :error="filesError"
          :expanded-paths="expandedPaths"
          :selected-paths="selectedPaths"
          :loading-paths="loadingPaths"
          :selection-state="selectionState"
          :format-bytes="formatBytes"
          :snapshot-operation-loading="snapshotOperationButtonLoading"
          :description="
            selectedSnapshot
              ? isNoChangeSnapshotReference(selectedSnapshot)
                ? t('backupTasks.detail.showingReferencedSnapshot')
                : selectedSnapshot.name || selectedSnapshot.id
              : '-'
          "
          show-selection-bar
          show-actions
          @retry="$emit('retry')"
          @toggle-directory="$emit('toggleDirectory', $event)"
          @toggle-selection="$emit('toggleSelection', $event)"
          @clear-selection="$emit('clearSelection')"
          @export-selected="$emit('exportSelected')"
          @index-snapshot="$emit('indexSnapshot')"
          @view-insights="$emit('viewInsights')"
          @analyze-ai-insights="$emit('analyzeAiInsights')"
        />
      </div>
    </template>
  </div>
</template>
