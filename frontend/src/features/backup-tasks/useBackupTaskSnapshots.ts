import { computed, ref, watch, type Ref } from "vue";
import { backupTasksApi } from "@/api";
import { getApiErrorMessage } from "@/utils/errors";
import {
  isNoChangeSnapshotReference,
  isSnapshotBrowsable,
  snapshotDisplayTime,
} from "@/features/backup-tasks/snapshotDisplay";
import { usePagination } from "@/composables/usePagination";
import type { BackupTask } from "@/types/backup";

type Translate = (key: string, params?: Record<string, any>) => string;
type AppStore = {
  success: (message: string) => void;
  error: (message: string) => void;
};

export type SnapshotGroupBy = "all" | "day" | "month" | "change" | "size";
export type SnapshotViewMode = "grid" | "timeline" | "blocks";

export function useBackupTaskSnapshots(options: {
  selectedTask: Ref<BackupTask | null>;
  t: Translate;
  appStore: AppStore;
  clearSelectedSnapshotIf: (predicate: (snapshot: any) => boolean) => void;
  snapshotGroupDescription: (snapshots: any[]) => string;
  snapshotGroupFor: (
    snapshot: any,
    mode: Exclude<SnapshotGroupBy, "all">,
  ) => { key: string; label: string };
}) {
  const {
    selectedTask,
    t,
    appStore,
    clearSelectedSnapshotIf,
    snapshotGroupDescription,
    snapshotGroupFor,
  } = options;
  const { getPageSize, setPageSize } = usePagination();
  const selectedTaskSnapshots = ref<any[]>([]);
  const collapseNoChangeSnapshots = ref(false);
  const snapshotGroupBy = ref<SnapshotGroupBy>("all");
  const snapshotViewMode = ref<SnapshotViewMode>("grid");
  const snapshotsLoading = ref(false);
  const snapshotOperationLoading = ref(false);
  const snapshotCurrentPage = ref(1);
  const snapshotPageSize = ref(getPageSize("backup-task-snapshots") || 50);
  const snapshotPageStorageKey = "backup-task-snapshots";

  watch(snapshotPageSize, (newSize) => {
    setPageSize(newSize, snapshotPageStorageKey);
  });

  const displayedTaskSnapshots = computed(() => {
    const snapshots = [...selectedTaskSnapshots.value].sort(
      (a, b) =>
        new Date(snapshotDisplayTime(b) || 0).getTime() -
        new Date(snapshotDisplayTime(a) || 0).getTime(),
    );
    if (!collapseNoChangeSnapshots.value) {
      return snapshots;
    }
    return snapshots.filter((snapshot) => !isNoChangeSnapshotReference(snapshot));
  });

  const hiddenNoChangeSnapshotCount = computed(
    () =>
      selectedTaskSnapshots.value.length - displayedTaskSnapshots.value.length,
  );

  const paginatedDisplayedTaskSnapshots = computed(() => {
    const start = (snapshotCurrentPage.value - 1) * snapshotPageSize.value;
    const end = start + snapshotPageSize.value;
    return displayedTaskSnapshots.value.slice(start, end);
  });

  const snapshotGroupOptions = computed(() => [
    { value: "all" as const, label: t("backupTasks.detail.groupAll") },
    { value: "day" as const, label: t("backupTasks.detail.groupByDay") },
    { value: "month" as const, label: t("backupTasks.detail.groupByMonth") },
    { value: "change" as const, label: t("backupTasks.detail.groupByChange") },
    { value: "size" as const, label: t("backupTasks.detail.groupBySize") },
  ]);

  const snapshotViewModeOptions = computed(() => [
    { value: "grid" as const, label: t("backupTasks.detail.gridView") },
    { value: "timeline" as const, label: t("backupTasks.detail.timelineView") },
    { value: "blocks" as const, label: t("backupTasks.detail.blocksView") },
  ]);

  const groupedDisplayedTaskSnapshots = computed(() => {
    const snapshots = paginatedDisplayedTaskSnapshots.value;
    if (snapshotGroupBy.value === "all") {
      return [
        {
          key: "all",
          label: t("backupTasks.detail.allSnapshots"),
          description: snapshotGroupDescription(snapshots),
          snapshots,
        },
      ];
    }

    const groupMap = new Map<string, { label: string; snapshots: any[] }>();
    for (const snapshot of snapshots) {
      const group = snapshotGroupFor(snapshot, snapshotGroupBy.value);
      if (!groupMap.has(group.key)) {
        groupMap.set(group.key, { label: group.label, snapshots: [] });
      }
      groupMap.get(group.key)?.snapshots.push(snapshot);
    }

    return Array.from(groupMap.entries()).map(([key, group]) => ({
      key,
      label: group.label,
      description: snapshotGroupDescription(group.snapshots),
      snapshots: group.snapshots,
    }));
  });

  watch([collapseNoChangeSnapshots, snapshotGroupBy, snapshotViewMode], () => {
    snapshotCurrentPage.value = 1;
  });

  watch(displayedTaskSnapshots, (snapshots) => {
    const totalPages = Math.max(
      1,
      Math.ceil(snapshots.length / snapshotPageSize.value),
    );
    if (snapshotCurrentPage.value > totalPages) {
      snapshotCurrentPage.value = totalPages;
    }
  });

  async function loadTaskSnapshots() {
    if (!selectedTask.value) return;
    snapshotsLoading.value = true;
    try {
      const pageSize = 500;
      let page = 1;
      const snapshots: any[] = [];
      while (selectedTask.value) {
        const response = await backupTasksApi.snapshots(selectedTask.value.id, {
          page,
          page_size: pageSize,
        });
        const data = response.data;
        const results = data.results || data || [];
        snapshots.push(...results);
        if (!data.next || results.length < pageSize) break;
        page += 1;
      }
      selectedTaskSnapshots.value = snapshots;
      snapshotCurrentPage.value = 1;
      clearSelectedSnapshotIf((snapshot) => !isSnapshotBrowsable(snapshot));
      clearSelectedSnapshotIf(
        (snapshot) =>
          collapseNoChangeSnapshots.value &&
          isNoChangeSnapshotReference(snapshot),
      );
    } catch (error) {
      console.error("Failed to fetch snapshots:", error);
    } finally {
      snapshotsLoading.value = false;
    }
  }

  async function syncSnapshotsFromKopia() {
    if (!selectedTask.value) return;
    snapshotOperationLoading.value = true;
    try {
      await backupTasksApi.syncSnapshots(selectedTask.value.id);
      appStore.success(t("backupTasks.detail.syncSnapshotsDispatched"));
    } catch (error) {
      appStore.error(getApiErrorMessage(error, t("common.updateFailed")));
    } finally {
      snapshotOperationLoading.value = false;
    }
  }

  async function evaluateRetentionNow() {
    if (!selectedTask.value) return;
    if (!window.confirm(t("backupTasks.detail.applyRetentionConfirm"))) return;
    snapshotOperationLoading.value = true;
    try {
      await backupTasksApi.evaluateRetention(selectedTask.value.id, {
        delete: true,
      });
      appStore.success(t("backupTasks.detail.retentionDispatched"));
      await loadTaskSnapshots();
    } catch (error) {
      appStore.error(getApiErrorMessage(error, t("common.updateFailed")));
    } finally {
      snapshotOperationLoading.value = false;
    }
  }

  async function runKopiaMaintenanceNow() {
    if (!selectedTask.value) return;
    snapshotOperationLoading.value = true;
    try {
      await backupTasksApi.runMaintenance(selectedTask.value.id, {
        full: true,
      });
      appStore.success(t("backupTasks.detail.maintenanceDispatched"));
    } catch (error) {
      appStore.error(getApiErrorMessage(error, t("common.updateFailed")));
    } finally {
      snapshotOperationLoading.value = false;
    }
  }

  function resetTaskSnapshots() {
    selectedTaskSnapshots.value = [];
  }

  return {
    selectedTaskSnapshots,
    collapseNoChangeSnapshots,
    snapshotGroupBy,
    snapshotViewMode,
    snapshotsLoading,
    snapshotOperationLoading,
    snapshotCurrentPage,
    snapshotPageSize,
    displayedTaskSnapshots,
    hiddenNoChangeSnapshotCount,
    groupedDisplayedTaskSnapshots,
    snapshotGroupOptions,
    snapshotViewModeOptions,
    loadTaskSnapshots,
    syncSnapshotsFromKopia,
    evaluateRetentionNow,
    runKopiaMaintenanceNow,
    resetTaskSnapshots,
  };
}
