<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  ArrowPathIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  DocumentIcon,
  ExclamationTriangleIcon,
  FolderIcon,
} from "@heroicons/vue/24/outline";

const props = withDefaults(
  defineProps<{
    selectedSnapshot: any | null;
    files: any[];
    loading: boolean;
    error: string;
    expandedPaths: Set<string>;
    selectedPaths?: Set<string>;
    loadingPaths: Set<string>;
    visibleFiles: any[];
    compact?: boolean;
    showHeader?: boolean;
    showSelectionBar?: boolean;
    showActions?: boolean;
    snapshotOperationLoading?: boolean;
    description?: string;
    selectionState: (file: any) => "checked" | "partial" | "none";
    formatBytes: (value: number) => string;
  }>(),
  {
    selectedPaths: () => new Set<string>(),
    compact: false,
    showHeader: true,
    showSelectionBar: false,
    showActions: false,
    snapshotOperationLoading: false,
    description: "",
  },
);

const emit = defineEmits<{
  retry: [];
  toggleDirectory: [file: any];
  toggleSelection: [file: any];
  clearSelection: [];
  exportSelected: [];
  indexSnapshot: [];
  viewInsights: [];
}>();

const { t } = useI18n();

const vIndeterminate = {
  mounted(el: HTMLInputElement, binding: { value: boolean }) {
    el.indeterminate = Boolean(binding.value);
  },
  updated(el: HTMLInputElement, binding: { value: boolean }) {
    el.indeterminate = Boolean(binding.value);
  },
};
</script>

<template>
  <div
    class="overflow-hidden border border-border bg-card"
    :class="props.compact ? 'border-x-0 border-b-0 rounded-none' : 'rounded-lg'"
  >
    <div
      v-if="props.showHeader"
      class="border-b border-border px-4 py-3"
      :class="props.showActions ? 'flex items-center justify-between' : ''"
    >
      <div>
        <h3 class="font-semibold text-foreground">
          {{ t("backupTasks.detail.fileBrowser") }}
        </h3>
        <p class="text-xs text-foreground-secondary">
          {{ props.description || "-" }}
        </p>
      </div>
      <div
        v-if="props.showActions && props.selectedSnapshot"
        class="flex items-center gap-2"
      >
        <button
          type="button"
          class="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-foreground hover:bg-hover disabled:opacity-50"
          :disabled="props.snapshotOperationLoading"
          @click="emit('indexSnapshot')"
        >
          {{ t("snapshotInsights.indexSnapshot") }}
        </button>
        <button
          type="button"
          class="rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-primary/90"
          @click="emit('viewInsights')"
        >
          {{ t("snapshotInsights.viewInsights") }}
        </button>
      </div>
    </div>
    <div
      v-if="props.selectedSnapshot"
      class="grid grid-cols-[minmax(0,1fr)_120px] gap-4 border-b border-border bg-background-secondary text-xs font-medium text-foreground-secondary"
      :class="props.compact ? 'border-y px-3 py-2' : 'px-4 py-2'"
    >
      <span>{{ t("common.name") }}</span>
      <span class="text-right">{{ t("backupTasks.progress.size") }}</span>
    </div>
    <div
      v-if="
        props.showSelectionBar &&
        props.selectedSnapshot &&
        props.selectedPaths.size > 0
      "
      class="flex flex-wrap items-center justify-between gap-3 border-b border-border bg-background px-4 py-2 text-sm"
    >
      <span class="text-foreground-secondary">
        {{
          t("recoveryExports.selectedForExport", {
            count: props.selectedPaths.size,
          })
        }}
      </span>
      <div class="flex items-center gap-2">
        <button
          type="button"
          class="rounded-lg border border-border px-3 py-1.5 text-sm font-medium text-foreground hover:bg-hover"
          @click="emit('clearSelection')"
        >
          {{ t("common.clear") }}
        </button>
        <button
          type="button"
          class="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700"
          @click="emit('exportSelected')"
        >
          {{ t("recoveryExports.exportDownload") }}
        </button>
      </div>
    </div>
    <div
      v-if="props.loading"
      class="text-center text-foreground-secondary"
      :class="props.compact ? 'p-5' : 'p-6'"
    >
      {{ t("common.loading") }}
    </div>
    <div
      v-else-if="!props.selectedSnapshot"
      class="text-center text-foreground-secondary"
      :class="props.compact ? 'p-5' : 'p-6'"
    >
      {{ t("backupTasks.detail.selectSnapshot") }}
    </div>
    <div v-else-if="props.error" class="text-center" :class="props.compact ? 'p-5' : 'p-6'">
      <ExclamationTriangleIcon class="mx-auto mb-3 h-8 w-8 text-warning" />
      <p class="text-sm font-medium text-foreground">
        {{ t("backupTasks.detail.snapshotFilesLoadFailed") }}
      </p>
      <p class="mx-auto mt-1 max-w-xl text-sm text-foreground-secondary">
        {{ props.error }}
      </p>
      <button
        type="button"
        class="mt-4 inline-flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-2 text-sm font-medium text-foreground hover:bg-hover"
        @click="emit('retry')"
      >
        <ArrowPathIcon class="h-4 w-4" />
        {{ t("common.retry") }}
      </button>
    </div>
    <div
      v-else-if="props.files.length === 0"
      class="text-center text-foreground-secondary"
      :class="props.compact ? 'p-5' : 'p-6'"
    >
      {{ t("backupTasks.detail.noSnapshotFiles") }}
    </div>
    <div v-else class="py-1">
      <div
        v-for="file in props.visibleFiles"
        :key="file.relative_path || file.id"
        class="group grid grid-cols-[minmax(0,1fr)_120px] gap-4 py-1.5 hover:bg-hover"
        :class="props.compact ? 'px-3' : 'px-4'"
      >
        <div
          class="flex min-w-0 items-center gap-1.5"
          :style="{ paddingLeft: `${(file.depth || 0) * 20}px` }"
        >
          <button
            type="button"
            class="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded hover:bg-background-tertiary"
            :class="file.is_dir ? 'visible' : 'invisible'"
            @click="emit('toggleDirectory', file)"
          >
            <ChevronDownIcon
              v-if="file.is_dir && props.expandedPaths.has(file.relative_path)"
              class="h-4 w-4 text-foreground-muted"
            />
            <ChevronRightIcon v-else class="h-4 w-4 text-foreground-muted" />
          </button>
          <ArrowPathIcon
            v-if="props.loadingPaths.has(file.relative_path)"
            class="h-4 w-4 shrink-0 animate-spin text-primary"
          />
          <input
            type="checkbox"
            class="h-4 w-4 shrink-0 rounded border-border text-primary focus:ring-primary"
            v-indeterminate="props.selectionState(file) === 'partial'"
            :checked="props.selectionState(file) === 'checked'"
            @change="emit('toggleSelection', file)"
          />
          <FolderIcon
            v-if="file.is_dir"
            class="h-4 w-4 shrink-0 text-amber-500"
          />
          <DocumentIcon
            v-else
            class="h-4 w-4 shrink-0 text-foreground-muted"
          />
          <div class="flex min-w-0 items-baseline gap-2">
            <button
              type="button"
              class="truncate text-left text-sm text-foreground hover:text-primary"
              @click="file.is_dir ? emit('toggleDirectory', file) : undefined"
            >
              {{ file.file_name || file.relative_path }}
            </button>
            <span
              class="hidden truncate text-xs text-foreground-muted xl:inline"
            >
              {{ file.relative_path }}
            </span>
          </div>
        </div>
        <span class="text-right text-sm tabular-nums text-foreground-secondary">
          {{ file.is_dir ? "-" : props.formatBytes(file.size || 0) }}
        </span>
      </div>
    </div>
  </div>
</template>
