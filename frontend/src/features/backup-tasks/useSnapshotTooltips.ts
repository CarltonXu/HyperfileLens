import { onUnmounted, ref } from "vue";

export function useSnapshotTooltips() {
  const snapshotHelpTooltip = ref<{
    key: string;
    top: number;
    left: number;
  } | null>(null);
  let snapshotHelpTooltipHideTimer: ReturnType<typeof setTimeout> | null = null;

  const snapshotHoverTooltip = ref<{
    snapshot: any;
    top: number;
    left: number;
    placement: "top" | "bottom";
  } | null>(null);
  let snapshotHoverTooltipHideTimer: ReturnType<typeof setTimeout> | null = null;

  function cancelSnapshotHelpTooltipHide() {
    if (snapshotHelpTooltipHideTimer) {
      clearTimeout(snapshotHelpTooltipHideTimer);
      snapshotHelpTooltipHideTimer = null;
    }
  }

  function showSnapshotHelpTooltip(
    event: MouseEvent | FocusEvent,
    key: string,
  ) {
    cancelSnapshotHelpTooltipHide();
    const target = event.currentTarget as HTMLElement | null;
    if (!target) return;
    const rect = target.getBoundingClientRect();
    snapshotHelpTooltip.value = {
      key,
      top: rect.bottom + 8,
      left: Math.min(
        Math.max(rect.left + rect.width / 2, 156),
        window.innerWidth - 156,
      ),
    };
  }

  function scheduleSnapshotHelpTooltipHide() {
    cancelSnapshotHelpTooltipHide();
    snapshotHelpTooltipHideTimer = setTimeout(() => {
      snapshotHelpTooltip.value = null;
    }, 120);
  }

  function cancelSnapshotHoverTooltipHide() {
    if (snapshotHoverTooltipHideTimer) {
      clearTimeout(snapshotHoverTooltipHideTimer);
      snapshotHoverTooltipHideTimer = null;
    }
  }

  function showSnapshotHoverTooltip(
    snapshot: any,
    event: MouseEvent | FocusEvent,
  ) {
    cancelSnapshotHoverTooltipHide();
    const target = event.currentTarget as HTMLElement | null;
    if (!target) return;
    const rect = target.getBoundingClientRect();
    const tooltipWidth = 288;
    const tooltipHeightEstimate = 220;
    const viewportPadding = 16;
    const left = Math.min(
      Math.max(rect.left + rect.width / 2, viewportPadding + tooltipWidth / 2),
      window.innerWidth - viewportPadding - tooltipWidth / 2,
    );
    const canShowBelow =
      rect.bottom + 10 + tooltipHeightEstimate < window.innerHeight;

    snapshotHoverTooltip.value = {
      snapshot,
      left,
      top: canShowBelow
        ? rect.bottom + 10
        : Math.max(rect.top - 10, viewportPadding),
      placement: canShowBelow ? "bottom" : "top",
    };
  }

  function scheduleSnapshotHoverTooltipHide() {
    cancelSnapshotHoverTooltipHide();
    snapshotHoverTooltipHideTimer = setTimeout(() => {
      snapshotHoverTooltip.value = null;
    }, 120);
  }

  onUnmounted(() => {
    cancelSnapshotHelpTooltipHide();
    cancelSnapshotHoverTooltipHide();
  });

  return {
    snapshotHelpTooltip,
    snapshotHoverTooltip,
    cancelSnapshotHelpTooltipHide,
    showSnapshotHelpTooltip,
    scheduleSnapshotHelpTooltipHide,
    cancelSnapshotHoverTooltipHide,
    showSnapshotHoverTooltip,
    scheduleSnapshotHoverTooltipHide,
  };
}
