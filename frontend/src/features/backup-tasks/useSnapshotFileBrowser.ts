import { ref } from "vue";
import { useI18n } from "vue-i18n";
import { backupTasksApi } from "@/api";
import { useAppStore } from "@/stores/app";
import { getApiErrorMessage } from "@/utils/errors";
import { isSnapshotBrowsable } from "./snapshotDisplay";

export function useSnapshotFileBrowser() {
  const { t } = useI18n();
  const appStore = useAppStore();

  const selectedSnapshot = ref<any | null>(null);
  const selectedSnapshotFiles = ref<any[]>([]);
  const snapshotFilesError = ref("");
  const snapshotFilesLoading = ref(false);
  const expandedSnapshotPaths = ref<Set<string>>(new Set());
  const selectedSnapshotPaths = ref<Set<string>>(new Set());
  const loadingSnapshotPaths = ref<Set<string>>(new Set());

  function resetSnapshotBrowser() {
    selectedSnapshot.value = null;
    selectedSnapshotFiles.value = [];
    snapshotFilesError.value = "";
    snapshotFilesLoading.value = false;
    expandedSnapshotPaths.value = new Set();
    selectedSnapshotPaths.value = new Set();
    loadingSnapshotPaths.value = new Set();
  }

  function clearSelectedSnapshotIf(predicate: (snapshot: any) => boolean) {
    if (selectedSnapshot.value && predicate(selectedSnapshot.value)) {
      resetSnapshotBrowser();
    }
  }

  async function loadSnapshotFiles(snapshot: any, path = "") {
    if (!snapshot?.id) return;
    if (!isSnapshotBrowsable(snapshot)) {
      appStore.error(t("backupTasks.detail.snapshotNotBrowsable"));
      return;
    }
    snapshotFilesError.value = "";
    if (!path) {
      snapshotFilesLoading.value = true;
    } else {
      loadingSnapshotPaths.value = new Set([
        ...loadingSnapshotPaths.value,
        path,
      ]);
    }
    try {
      const response = await backupTasksApi.listFiles(snapshot.id, path);
      selectedSnapshot.value = snapshot;
      const files = response.data.results || response.data || [];
      if (!path) {
        selectedSnapshotFiles.value = normalizeSnapshotFiles(files, "");
        expandedSnapshotPaths.value = new Set();
        selectedSnapshotPaths.value = new Set();
        loadingSnapshotPaths.value = new Set();
      } else {
        mergeSnapshotChildren(path, files);
        expandedSnapshotPaths.value = new Set([
          ...expandedSnapshotPaths.value,
          path,
        ]);
      }
    } catch (error) {
      const message = getApiErrorMessage(
        error,
        t("backupTasks.detail.snapshotFilesLoadFailed"),
      );
      appStore.error(message);
      if (!path) {
        snapshotFilesError.value = message;
        selectedSnapshot.value = snapshot;
        selectedSnapshotFiles.value = [];
        expandedSnapshotPaths.value = new Set();
        selectedSnapshotPaths.value = new Set();
      }
    } finally {
      if (!path) {
        snapshotFilesLoading.value = false;
      } else {
        const next = new Set(loadingSnapshotPaths.value);
        next.delete(path);
        loadingSnapshotPaths.value = next;
      }
    }
  }

  function normalizeSnapshotFiles(files: any[], parentPath: string) {
    return files.map((file: any) => {
      const rawPath = file.relative_path || file.path || file.file_name || "";
      const rawCleanPath = String(rawPath)
        .replace(/^\/+/, "")
        .replace(/\/+$/, "");
      const cleanPath =
        parentPath && rawCleanPath && !rawCleanPath.startsWith(`${parentPath}/`)
          ? `${parentPath}/${rawCleanPath}`
          : rawCleanPath;
      const name =
        file.file_name ||
        rawCleanPath.split("/").filter(Boolean).pop() ||
        cleanPath;
      const type = file.type || file.entry_type || "";
      const isDirectory =
        file.is_dir === true ||
        type === "d" ||
        type === "dir" ||
        type === "directory";
      return {
        ...file,
        id: file.id || cleanPath || `${parentPath}/${name}`,
        relative_path: cleanPath,
        file_name: name,
        parent_path: parentPath,
        depth: parentPath
          ? parentPath.split("/").filter(Boolean).length + 1
          : 0,
        is_dir: isDirectory,
        children_loaded: false,
      };
    });
  }

  function mergeSnapshotChildren(parentPath: string, files: any[]) {
    const children = normalizeSnapshotFiles(files, parentPath);
    const withoutOldChildren = selectedSnapshotFiles.value.filter(
      (file) => file.parent_path !== parentPath,
    );
    const parentIndex = withoutOldChildren.findIndex(
      (file) => file.relative_path === parentPath,
    );
    if (parentIndex === -1) {
      selectedSnapshotFiles.value = withoutOldChildren;
      return;
    }
    withoutOldChildren[parentIndex] = {
      ...withoutOldChildren[parentIndex],
      children_loaded: true,
    };
    withoutOldChildren.splice(parentIndex + 1, 0, ...children);
    selectedSnapshotFiles.value = withoutOldChildren;
  }

  function visibleSnapshotFiles() {
    return selectedSnapshotFiles.value.filter((file) => {
      if (!file.parent_path) return true;
      const ancestors = file.parent_path.split("/").filter(Boolean);
      let current = "";
      for (const part of ancestors) {
        current = current ? `${current}/${part}` : part;
        if (!expandedSnapshotPaths.value.has(current)) return false;
      }
      return true;
    });
  }

  async function toggleSnapshotDirectory(file: any) {
    if (!file.is_dir) return;
    const path = file.relative_path;
    const next = new Set(expandedSnapshotPaths.value);
    if (next.has(path)) {
      next.delete(path);
      expandedSnapshotPaths.value = next;
      return;
    }
    if (!file.children_loaded && selectedSnapshot.value) {
      await loadSnapshotFiles(selectedSnapshot.value, path);
      return;
    }
    next.add(path);
    expandedSnapshotPaths.value = next;
  }

  function toggleSnapshotPathSelection(file: any) {
    const path = file.relative_path;
    const next = new Set(selectedSnapshotPaths.value);
    const currentlySelected = getSnapshotSelectionState(file) === "checked";
    if (currentlySelected) {
      removeSnapshotPathAndDescendants(next, path);
    } else {
      removeSnapshotDescendants(next, path);
      next.add(path);
    }
    selectedSnapshotPaths.value = next;
  }

  function removeSnapshotPathAndDescendants(
    selected: Set<string>,
    path: string,
  ) {
    selected.delete(path);
    for (const item of [...selected]) {
      if (item.startsWith(`${path}/`)) selected.delete(item);
    }
    const ancestor = findSelectedSnapshotAncestor(path, selected);
    if (ancestor) {
      selected.delete(ancestor);
      const descendants = selectedSnapshotFiles.value.filter((file) =>
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

  function removeSnapshotDescendants(selected: Set<string>, path: string) {
    for (const item of [...selected]) {
      if (item.startsWith(`${path}/`)) selected.delete(item);
    }
  }

  function findSelectedSnapshotAncestor(path: string, selected: Set<string>) {
    const parts = path.split("/").filter(Boolean);
    while (parts.length > 1) {
      parts.pop();
      const ancestor = parts.join("/");
      if (selected.has(ancestor)) return ancestor;
    }
    return "";
  }

  function hasSelectedSnapshotAncestor(path: string) {
    return Boolean(
      findSelectedSnapshotAncestor(path, selectedSnapshotPaths.value),
    );
  }

  function getSnapshotSelectionState(
    file: any,
  ): "checked" | "partial" | "none" {
    const path = file.relative_path;
    const selected = selectedSnapshotPaths.value;
    if (selected.has(path) || hasSelectedSnapshotAncestor(path)) {
      return "checked";
    }
    if (!file.is_dir) return "none";
    const descendants = selectedSnapshotFiles.value.filter((item) =>
      item.relative_path?.startsWith(`${path}/`),
    );
    if (
      descendants.some(
        (item) =>
          selected.has(item.relative_path) ||
          hasSelectedSnapshotAncestor(item.relative_path),
      )
    ) {
      return "partial";
    }
    return "none";
  }

  function clearSnapshotPathSelection() {
    selectedSnapshotPaths.value = new Set();
  }

  return {
    selectedSnapshot,
    selectedSnapshotFiles,
    snapshotFilesError,
    snapshotFilesLoading,
    expandedSnapshotPaths,
    selectedSnapshotPaths,
    loadingSnapshotPaths,
    resetSnapshotBrowser,
    clearSelectedSnapshotIf,
    loadSnapshotFiles,
    visibleSnapshotFiles,
    toggleSnapshotDirectory,
    toggleSnapshotPathSelection,
    getSnapshotSelectionState,
    clearSnapshotPathSelection,
  };
}
