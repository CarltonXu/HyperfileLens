type Translate = (key: string, params?: Record<string, any>) => string;

export function useGatewayFormatting(t: Translate) {
  const statusColors: Record<string, string> = {
    pending:
      "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
    installing:
      "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    active:
      "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
    inactive:
      "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
    online:
      "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
    offline: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    error: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    maintenance:
      "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  };

  function getStatusLabel(status: string): string {
    const labels: Record<string, string> = {
      pending: t("gateways.statusPending"),
      installing: t("gateways.statusInstalling"),
      online: t("gateways.statusOnline"),
      offline: t("gateways.statusOffline"),
      error: t("gateways.statusError"),
      maintenance: t("gateways.statusMaintenance"),
    };
    return labels[status] || status;
  }

  function formatBytes(bytes: number): string {
    if (!bytes) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  }

  function formatDate(dateStr: string): string {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleString();
  }

  return {
    statusColors,
    getStatusLabel,
    formatBytes,
    formatDate,
  };
}
