<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import {
  ArrowPathIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  DocumentIcon,
  ExclamationTriangleIcon,
  FolderIcon,
  FolderOpenIcon,
} from "@heroicons/vue/24/outline";
import type { RecoveryScope } from "@/types/recovery";

interface SnapshotFile {
  id?: string;
  relative_path: string;
  file_name?: string;
  parent_path?: string;
  depth?: number;
  size?: number;
  is_dir?: boolean;
  children_loaded?: boolean;
}

const props = defineProps<{
  restoreScope?: RecoveryScope;
  selectedPaths?: string[];
  files: SnapshotFile[];
  loading: boolean;
  error: string;
  loadingPaths: Set<string>;
  formatBytes: (bytes: number) => string;
}>();

const emit = defineEmits<{
  "update:restoreScope": [value: RecoveryScope];
  "update:selectedPaths": [value: string[]];
  loadFiles: [path?: string];
}>();

const { t } = useI18n();
const expandedPaths = ref<Set<string>>(new Set());

const selectedPathSet = computed(() => new Set(props.selectedPaths || []));

const visibleFiles = computed(() => {
  return props.files.filter((file) => {
    if (!file.parent_path) return true;
    const ancestors = file.parent_path.split("/").filter(Boolean);
    let current = "";
    for (const part of ancestors) {
      current = current ? `${current}/${part}` : part;
      if (!expandedPaths.value.has(current)) return false;
    }
    return true;
  });
});

const vIndeterminate = {
  mounted(el: HTMLInputElement, binding: { value: boolean }) {
    el.indeterminate = Boolean(binding.value);
  },
  updated(el: HTMLInputElement, binding: { value: boolean }) {
    el.indeterminate = Boolean(binding.value);
  },
};

function setRestoreScope(scope: RecoveryScope) {
  emit("update:restoreScope", scope);
  if (scope === "selected_paths" && props.files.length === 0) {
    emit("loadFiles");
  }
}

function refreshFiles() {
  expandedPaths.value = new Set();
  emit("loadFiles");
}

function toggleDirectory(file: SnapshotFile) {
  if (!file.is_dir) return;
  const path = file.relative_path;
  const next = new Set(expandedPaths.value);
  if (next.has(path)) {
    next.delete(path);
    expandedPaths.value = next;
    return;
  }
  next.add(path);
  expandedPaths.value = next;
  if (!file.children_loaded) {
    emit("loadFiles", path);
  }
}

function togglePathSelection(file: SnapshotFile) {
  const path = file.relative_path;
  const next = new Set(props.selectedPaths || []);
  const currentlySelected = getSelectionState(file) === "checked";
  if (currentlySelected) {
    removePathAndDescendants(next, path);
  } else {
    removeDescendants(next, path);
    next.add(path);
  }
  emit("update:selectedPaths", [...next]);
}

function removePathAndDescendants(selected: Set<string>, path: string) {
  selected.delete(path);
  for (const item of [...selected]) {
    if (item.startsWith(`${path}/`)) selected.delete(item);
  }
  const ancestor = findSelectedAncestor(path, selected);
  if (ancestor) {
    selected.delete(ancestor);
    const descendants = props.files.filter((file) =>
      file.relative_path?.startsWith(`${ancestor}/`),
    );
    for (const file of descendants) {
      if (
        file.relative_path !== path &&
        !file.relative_path.startsWith(`${path}/`)
      ) {
        selected.add(file.relative_path);
      }
    }
  }
}

function removeDescendants(selected: Set<string>, path: string) {
  for (const item of [...selected]) {
    if (item.startsWith(`${path}/`)) selected.delete(item);
  }
}

function findSelectedAncestor(path: string, selected: Set<string>) {
  const parts = path.split("/").filter(Boolean);
  while (parts.length > 1) {
    parts.pop();
    const ancestor = parts.join("/");
    if (selected.has(ancestor)) return ancestor;
  }
  return "";
}

function hasSelectedAncestor(path: string) {
  return Boolean(findSelectedAncestor(path, selectedPathSet.value));
}

function getSelectionState(file: SnapshotFile): "checked" | "partial" | "none" {
  const path = file.relative_path;
  const selected = selectedPathSet.value;
  if (selected.has(path) || hasSelectedAncestor(path)) return "checked";
  if (!file.is_dir) return "none";
  const descendants = props.files.filter((item) =>
    item.relative_path?.startsWith(`${path}/`),
  );
  if (
    descendants.some(
      (item) =>
        selected.has(item.relative_path) || hasSelectedAncestor(item.relative_path),
    )
  ) {
    return "partial";
  }
  return "none";
}
</script>

<template>
  <section class="rounded-lg border border-border bg-background-secondary/40 p-4">
    <div class="flex items-start gap-3 mb-4">
      <FolderOpenIcon class="w-5 h-5 text-emerald-600 mt-0.5" />
      <div>
        <h3 class="text-sm font-semibold text-foreground">
          {{ t("recoveryTasks.scope.title") }}
        </h3>
        <p class="text-xs text-foreground-secondary mt-1">
          {{ t("recoveryTasks.wizard.scopeHelp") }}
        </p>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <label
        :class="[
          'flex items-start gap-3 rounded-lg border p-3 cursor-pointer',
          props.restoreScope === 'entire_snapshot'
            ? 'border-emerald-500 bg-emerald-50/60 dark:bg-emerald-950/20'
            : 'border-border bg-card hover:bg-hover',
        ]"
      >
        <input
          :checked="props.restoreScope === 'entire_snapshot'"
          type="radio"
          value="entire_snapshot"
          class="mt-1 text-emerald-600"
          @change="setRestoreScope('entire_snapshot')"
        />
        <span>
          <span class="block text-sm font-medium text-foreground">
            {{ t("recoveryTasks.scope.entire") }}
          </span>
          <span class="block text-xs text-foreground-secondary mt-1">
            {{ t("recoveryTasks.scope.entireHelp") }}
          </span>
        </span>
      </label>
      <label
        :class="[
          'flex items-start gap-3 rounded-lg border p-3 cursor-pointer',
          props.restoreScope === 'selected_paths'
            ? 'border-emerald-500 bg-emerald-50/60 dark:bg-emerald-950/20'
            : 'border-border bg-card hover:bg-hover',
        ]"
      >
        <input
          :checked="props.restoreScope === 'selected_paths'"
          type="radio"
          value="selected_paths"
          class="mt-1 text-emerald-600"
          @change="setRestoreScope('selected_paths')"
        />
        <span>
          <span class="block text-sm font-medium text-foreground">
            {{ t("recoveryTasks.scope.selected") }}
          </span>
          <span class="block text-xs text-foreground-secondary mt-1">
            {{ t("recoveryTasks.scope.selectedHelp") }}
          </span>
        </span>
      </label>
    </div>

    <div
      v-if="props.restoreScope === 'selected_paths'"
      class="mt-5 rounded-lg border border-border bg-card overflow-hidden"
    >
      <div class="px-4 py-3 border-b border-border flex items-center justify-between gap-3">
        <div>
          <h4 class="text-sm font-semibold text-foreground">
            {{ t("recoveryTasks.scope.fileTreeTitle") }}
          </h4>
          <p class="text-xs text-foreground-secondary mt-1">
            {{ t("recoveryTasks.scope.fileTreeHelp") }}
          </p>
        </div>
        <button
          type="button"
          class="inline-flex items-center gap-2 px-3 py-2 text-sm border border-border rounded-lg hover:bg-hover"
          @click="refreshFiles"
        >
          <ArrowPathIcon
            :class="['w-4 h-4', props.loading ? 'animate-spin' : '']"
          />
          {{ t("common.refresh") }}
        </button>
      </div>
      <div class="px-4 py-2 border-b border-border bg-background-secondary/40 flex items-center justify-between text-xs text-foreground-secondary">
        <span>
          {{ (props.selectedPaths || []).length }}
          {{ t("recoveryTasks.scope.selectedCount") }}
        </span>
        <button
          v-if="(props.selectedPaths || []).length"
          type="button"
          class="text-emerald-600 hover:text-emerald-700"
          @click="emit('update:selectedPaths', [])"
        >
          {{ t("common.clear") || "Clear" }}
        </button>
      </div>
      <div v-if="props.loading" class="p-8 flex justify-center">
        <div
          class="w-7 h-7 border-4 border-emerald-200 border-t-emerald-600 rounded-full animate-spin"
        />
      </div>
      <div v-else-if="props.error" class="p-6 text-center">
        <ExclamationTriangleIcon class="w-8 h-8 text-red-500 mx-auto mb-3" />
        <p class="text-sm font-medium text-foreground">
          {{ t("recoveryTasks.messages.snapshotFilesLoadFailed") }}
        </p>
        <p class="text-xs text-foreground-secondary mt-1">
          {{ props.error }}
        </p>
      </div>
      <div v-else-if="props.files.length === 0" class="p-8 text-center">
        <FolderIcon class="w-8 h-8 text-slate-400 mx-auto mb-3" />
        <p class="text-sm font-medium text-foreground">
          {{ t("recoveryTasks.scope.noFilesTitle") }}
        </p>
        <p class="text-xs text-foreground-secondary mt-1">
          {{ t("recoveryTasks.scope.noFilesDescription") }}
        </p>
        <button
          type="button"
          class="mt-4 inline-flex items-center gap-2 px-3 py-2 text-sm border border-border rounded-lg hover:bg-hover"
          @click="emit('loadFiles')"
        >
          <ArrowPathIcon class="w-4 h-4" />
          {{ t("recoveryTasks.scope.loadFiles") }}
        </button>
      </div>
      <div v-else class="max-h-[360px] overflow-y-auto py-1">
        <div
          v-for="file in visibleFiles"
          :key="file.relative_path || file.id"
          class="grid grid-cols-[minmax(0,1fr)_120px] gap-4 px-4 py-1.5 hover:bg-hover"
        >
          <div
            class="flex items-center gap-1.5 min-w-0"
            :style="{ paddingLeft: `${(file.depth || 0) * 20}px` }"
          >
            <button
              type="button"
              class="w-5 h-5 inline-flex items-center justify-center rounded hover:bg-background-tertiary shrink-0"
              :class="file.is_dir ? 'visible' : 'invisible'"
              @click="toggleDirectory(file)"
            >
              <ChevronDownIcon
                v-if="file.is_dir && expandedPaths.has(file.relative_path)"
                class="w-4 h-4 text-foreground-secondary"
              />
              <ChevronRightIcon
                v-else
                class="w-4 h-4 text-foreground-secondary"
              />
            </button>
            <ArrowPathIcon
              v-if="props.loadingPaths.has(file.relative_path)"
              class="w-4 h-4 animate-spin text-emerald-600 shrink-0"
            />
            <input
              v-indeterminate="getSelectionState(file) === 'partial'"
              type="checkbox"
              class="h-4 w-4 rounded border-border text-emerald-600 focus:ring-emerald-500 shrink-0"
              :checked="getSelectionState(file) === 'checked'"
              @change="togglePathSelection(file)"
            />
            <FolderIcon
              v-if="file.is_dir"
              class="w-4 h-4 text-amber-500 shrink-0"
            />
            <DocumentIcon
              v-else
              class="w-4 h-4 text-foreground-secondary shrink-0"
            />
            <button
              type="button"
              class="text-left text-sm text-foreground truncate hover:text-emerald-600"
              @click="file.is_dir ? toggleDirectory(file) : undefined"
            >
              {{ file.file_name || file.relative_path }}
            </button>
          </div>
          <span class="text-sm text-foreground-secondary text-right tabular-nums">
            {{ file.is_dir ? "-" : props.formatBytes(file.size || 0) }}
          </span>
        </div>
      </div>
    </div>
  </section>
</template>
