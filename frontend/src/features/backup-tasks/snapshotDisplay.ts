export function snapshotDisplayTime(snapshot: any) {
  return (
    snapshot?.metadata?.snapshot_time ||
    snapshot?.metadata?.kopia_start_time ||
    snapshot?.metadata?.kopia_snapshot?.startTime ||
    snapshot?.metadata?.kopia_end_time ||
    snapshot?.metadata?.kopia_snapshot?.endTime ||
    snapshot?.created_at ||
    snapshot?.metadata?.last_seen_at
  );
}

export function isNoChangeSnapshotReference(snapshot: any) {
  return (
    snapshot?.metadata?.no_changes === true ||
    snapshot?.metadata?.last_no_changes === true
  );
}

export function snapshotDisplaySize(snapshot: any) {
  return isNoChangeSnapshotReference(snapshot)
    ? 0
    : Number(snapshot?.total_size || 0);
}

export function snapshotDisplayFileCount(snapshot: any) {
  return isNoChangeSnapshotReference(snapshot)
    ? 0
    : Number(snapshot?.file_count || 0);
}

export function snapshotReferencedId(snapshot: any) {
  return (
    snapshot?.metadata?.referenced_snapshot_id ||
    snapshot?.metadata?.referenced_manifest_id ||
    snapshot?.metadata?.referenced_storage_path ||
    snapshot?.metadata?.root_object_id ||
    snapshot?.storage_path ||
    snapshot?.version ||
    ""
  );
}

export function snapshotStatusClass(snapshot: any) {
  const status = snapshot?.snapshot_status || "available";
  const classes: Record<string, string> = {
    available:
      "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300",
    pending_prune:
      "bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300",
    missing:
      "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
    pruned: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
    delete_failed:
      "bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-300",
  };
  return classes[status] || classes.available;
}

export function isSnapshotBrowsable(snapshot: any) {
  return (snapshot?.snapshot_status || "available") === "available";
}

export function snapshotCardClass(snapshot: any, selectedId?: string | number) {
  const status = snapshot?.snapshot_status || "available";
  const selected = selectedId === snapshot?.id;
  if (status === "available") {
    return selected
      ? "border-emerald-500 bg-emerald-50 text-emerald-950 shadow-sm dark:bg-emerald-950/30 dark:text-emerald-50"
      : "border-border bg-card hover:border-emerald-400 hover:bg-emerald-50/70 dark:hover:bg-emerald-950/20";
  }
  if (status === "pending_prune") {
    return "cursor-not-allowed border-amber-300 bg-amber-50/70 text-amber-950 opacity-90 dark:border-amber-900/60 dark:bg-amber-950/20 dark:text-amber-50";
  }
  if (status === "delete_failed") {
    return "cursor-not-allowed border-red-300 bg-red-50/70 text-red-950 opacity-90 dark:border-red-900/60 dark:bg-red-950/20 dark:text-red-50";
  }
  return "cursor-not-allowed border-slate-300 bg-slate-100/80 text-slate-600 opacity-75 dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-400";
}

export function snapshotTimelineClass(
  snapshot: any,
  selectedId?: string | number,
) {
  const status = snapshot?.snapshot_status || "available";
  const selected = selectedId === snapshot?.id;
  if (status === "available") {
    return selected
      ? "border-emerald-500 bg-emerald-50/70 dark:bg-emerald-950/20"
      : "border-border hover:bg-hover";
  }
  if (status === "pending_prune") {
    return "border-amber-300 bg-amber-50/70 opacity-90 dark:border-amber-900/60 dark:bg-amber-950/20";
  }
  if (status === "delete_failed") {
    return "border-red-300 bg-red-50/70 opacity-90 dark:border-red-900/60 dark:bg-red-950/20";
  }
  return "border-slate-300 bg-slate-100/80 opacity-75 dark:border-slate-700 dark:bg-slate-900/50";
}

export function snapshotTimelineDotClass(
  snapshot: any,
  selectedId?: string | number,
) {
  const status = snapshot?.snapshot_status || "available";
  if (selectedId === snapshot?.id) {
    return "border-emerald-500 ring-4 ring-emerald-100 dark:ring-emerald-950/40";
  }
  if (status === "pending_prune") return "border-amber-500";
  if (status === "delete_failed") return "border-red-500";
  if (status !== "available") return "border-slate-400";
  return isNoChangeSnapshotReference(snapshot) ? "border-amber-500" : "border-emerald-400";
}

export function snapshotBlockClass(snapshot: any, selectedId?: string | number) {
  const status = snapshot?.snapshot_status || "available";
  const selected = selectedId === snapshot?.id;
  const selectedRing =
    "ring-2 ring-offset-1 ring-slate-900/60 dark:ring-slate-100/80 dark:ring-offset-background";

  if (status === "available") {
    if (isNoChangeSnapshotReference(snapshot)) {
      return selected
        ? `bg-sky-400 hover:bg-sky-500 dark:bg-sky-500 dark:hover:bg-sky-400 ${selectedRing}`
        : "bg-sky-300 hover:bg-sky-400 dark:bg-sky-600 dark:hover:bg-sky-500";
    }
    return selected
      ? `bg-emerald-500 hover:bg-emerald-600 dark:bg-emerald-500 dark:hover:bg-emerald-400 ${selectedRing}`
      : "bg-emerald-400 hover:bg-emerald-500 dark:bg-emerald-600 dark:hover:bg-emerald-500";
  }

  if (status === "pending_prune") {
    return selected
      ? `bg-amber-400 dark:bg-amber-500 ${selectedRing}`
      : "bg-amber-300 hover:bg-amber-400 dark:bg-amber-600 dark:hover:bg-amber-500";
  }

  if (status === "delete_failed") {
    return selected
      ? `bg-red-500 dark:bg-red-500 ${selectedRing}`
      : "bg-red-400 hover:bg-red-500 dark:bg-red-700 dark:hover:bg-red-600";
  }

  return selected
    ? `bg-slate-500 dark:bg-slate-400 ${selectedRing}`
    : "bg-slate-300 hover:bg-slate-400 dark:bg-slate-700 dark:hover:bg-slate-600";
}
