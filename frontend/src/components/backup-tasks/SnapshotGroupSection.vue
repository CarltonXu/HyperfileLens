<script setup lang="ts">
import SnapshotBlocks from "./SnapshotBlocks.vue";
import SnapshotGrid from "./SnapshotGrid.vue";
import SnapshotTimeline from "./SnapshotTimeline.vue";

type SnapshotViewMode = "grid" | "timeline" | "blocks";
type SnapshotGroupBy = "all" | "day" | "month" | "change" | "size";

defineProps<{
  group: {
    key: string;
    label: string;
    description: string;
    snapshots: any[];
  };
  groupBy: SnapshotGroupBy;
  viewMode: SnapshotViewMode;
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
  formatCompactDateTime: (value?: string | null) => string;
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
</script>

<template>
  <section class="space-y-2.5">
    <div
      v-if="groupBy !== 'all'"
      class="flex items-center justify-between gap-3 border-b border-border pb-2"
    >
      <div>
        <h4 class="text-sm font-semibold text-foreground">
          {{ group.label }}
        </h4>
        <p class="mt-0.5 text-xs text-foreground-secondary">
          {{ group.description }}
        </p>
      </div>
    </div>

    <SnapshotGrid
      v-if="viewMode === 'grid'"
      :snapshots="group.snapshots"
      :selected-snapshot-id="selectedSnapshot?.id"
      :latest-snapshot-id="latestSnapshotId"
      :format-compact-date-time="formatCompactDateTime"
      :format-bytes="formatBytes"
      @select="$emit('select', $event)"
      @hover="(snapshot, event) => $emit('hover', snapshot, event)"
      @hide-hover="$emit('hideHover')"
    />

    <SnapshotTimeline
      v-else-if="viewMode === 'timeline'"
      :snapshots="group.snapshots"
      :selected-snapshot="selectedSnapshot"
      :latest-snapshot-id="latestSnapshotId"
      :files="files"
      :visible-files="visibleFiles"
      :files-loading="filesLoading"
      :files-error="filesError"
      :expanded-paths="expandedPaths"
      :selected-paths="selectedPaths"
      :loading-paths="loadingPaths"
      :selection-state="selectionState"
      :format-date-time="formatDateTime"
      :format-bytes="formatBytes"
      @select="$emit('select', $event)"
      @hover="(snapshot, event) => $emit('hover', snapshot, event)"
      @hide-hover="$emit('hideHover')"
      @retry="$emit('retry')"
      @toggle-directory="$emit('toggleDirectory', $event)"
      @toggle-selection="$emit('toggleSelection', $event)"
    />

    <SnapshotBlocks
      v-else-if="viewMode === 'blocks'"
      :snapshots="group.snapshots"
      :selected-snapshot-id="selectedSnapshot?.id"
      :format-date-time="formatDateTime"
      @select="$emit('select', $event)"
      @hover="(snapshot, event) => $emit('hover', snapshot, event)"
      @hide-hover="$emit('hideHover')"
    />
  </section>
</template>
