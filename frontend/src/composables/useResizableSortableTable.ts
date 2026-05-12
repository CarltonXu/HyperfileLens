import { computed, onUnmounted, ref, type ComputedRef, type Ref } from "vue";
import {
  ArrowsUpDownIcon,
  ChevronDownIcon,
  ChevronUpIcon,
} from "@heroicons/vue/24/outline";

export interface TableColumn<Key extends string> {
  key: Key;
  label: string;
  min?: number;
  max?: number;
  width?: number;
  sortable?: boolean;
  align?: "left" | "right" | "center";
}

type MaybeRef<T> = T | Ref<T> | ComputedRef<T>;

function resolveMaybeRef<T>(value: MaybeRef<T>): T {
  if (value && typeof value === "object" && "value" in value) {
    return value.value;
  }
  return value as T;
}

function estimateTextWidth(text: string, extra = 48) {
  let width = extra;
  for (const char of text) {
    width += /[\u4e00-\u9fff]/.test(char) ? 14 : 8;
  }
  return width;
}

function loadWidths<Key extends string>(
  storageKey: string,
): Partial<Record<Key, number>> {
  try {
    const stored = localStorage.getItem(storageKey);
    if (!stored) return {};
    const parsed = JSON.parse(stored) as Partial<Record<Key, number>>;
    return Object.fromEntries(
      Object.entries(parsed).filter(([, width]) => typeof width === "number"),
    ) as Partial<Record<Key, number>>;
  } catch {
    return {};
  }
}

export function useResizableSortableTable<Row, Key extends string>(options: {
  storageKey: string;
  columns: MaybeRef<Array<TableColumn<Key>>>;
  rows: MaybeRef<Row[]>;
  defaultSort?: { key: Key; direction?: "asc" | "desc" };
  getSortValue?: (
    row: Row,
    key: Key,
  ) => string | number | Date | null | undefined;
  getColumnText?: (row: Row, key: Key) => string;
  sampleSize?: number;
  minTableWidth?: number;
}) {
  const sort = ref({
    key: options.defaultSort?.key ?? resolveMaybeRef(options.columns)[0]?.key,
    direction: options.defaultSort?.direction ?? "asc",
  }) as Ref<{ key: Key; direction: "asc" | "desc" }>;

  const manualWidths = ref<Partial<Record<Key, number>>>(
    loadWidths<Key>(options.storageKey),
  );
  const resizingColumn = ref<Key | null>(null);
  let removeResizeListeners: (() => void) | null = null;

  const columns = computed(() => resolveMaybeRef(options.columns));
  const sourceRows = computed(() => resolveMaybeRef(options.rows));

  function saveWidths() {
    try {
      localStorage.setItem(
        options.storageKey,
        JSON.stringify(manualWidths.value),
      );
    } catch {
      // Ignore storage errors in private browsing or restricted environments.
    }
  }

  function getColumnConfig(key: Key) {
    return columns.value.find((column) => column.key === key);
  }

  function normalizeSortValue(
    value: string | number | Date | null | undefined,
  ) {
    if (value instanceof Date) return value.getTime();
    if (value === null || value === undefined) return "";
    return value;
  }

  const sortedRows = computed(() => {
    const sortColumn = getColumnConfig(sort.value.key);
    if (!sortColumn || sortColumn.sortable === false) {
      return [...sourceRows.value];
    }

    const multiplier = sort.value.direction === "asc" ? 1 : -1;
    return [...sourceRows.value].sort((a, b) => {
      const aValue = normalizeSortValue(
        options.getSortValue?.(a, sort.value.key) ?? "",
      );
      const bValue = normalizeSortValue(
        options.getSortValue?.(b, sort.value.key) ?? "",
      );

      if (typeof aValue === "number" && typeof bValue === "number") {
        return (aValue - bValue) * multiplier;
      }

      return (
        String(aValue).localeCompare(String(bValue), undefined, {
          numeric: true,
          sensitivity: "base",
        }) * multiplier
      );
    });
  });

  const autoWidths = computed<Record<Key, number>>(() => {
    const widths = {} as Record<Key, number>;
    const sampleRows = sortedRows.value.slice(0, options.sampleSize ?? 80);

    for (const column of columns.value) {
      const min = column.min ?? 96;
      const max = column.max ?? 720;
      const configuredWidth = column.width;

      if (configuredWidth) {
        widths[column.key] = Math.min(Math.max(configuredWidth, min), max);
        continue;
      }

      const headerWidth = estimateTextWidth(column.label, 56);
      const cellWidth = sampleRows.reduce((maxWidth, row) => {
        const text = options.getColumnText?.(row, column.key) ?? "";
        return Math.max(maxWidth, estimateTextWidth(text));
      }, headerWidth);

      widths[column.key] = Math.min(Math.max(cellWidth, min), max);
    }

    return widths;
  });

  const columnWidths = computed<Record<Key, number>>(
    () =>
      ({ ...autoWidths.value, ...manualWidths.value }) as Record<Key, number>,
  );

  const tableMinWidth = computed(() => {
    const total = (Object.values(columnWidths.value) as number[]).reduce(
      (sum: number, width: number) => sum + width,
      0,
    );
    return `${Math.max(total, options.minTableWidth ?? 720)}px`;
  });

  function columnStyle(key: Key) {
    const width = columnWidths.value[key];
    return {
      width: `${width}px`,
      minWidth: `${width}px`,
    };
  }

  function toggleSort(key: Key) {
    const column = getColumnConfig(key);
    if (column?.sortable === false) return;

    if (sort.value.key === key) {
      sort.value.direction = sort.value.direction === "asc" ? "desc" : "asc";
      return;
    }
    sort.value = { key, direction: "asc" };
  }

  function getSortIcon(key: Key) {
    if (sort.value.key !== key) return ArrowsUpDownIcon;
    return sort.value.direction === "asc" ? ChevronUpIcon : ChevronDownIcon;
  }

  function setColumnWidth(key: Key, width: number) {
    const column = getColumnConfig(key);
    const min = column?.min ?? 96;
    const max = column?.max ?? 720;
    manualWidths.value = {
      ...manualWidths.value,
      [key]: Math.round(Math.min(Math.max(width, min), max)),
    };
  }

  function resetColumnWidth(key: Key) {
    const nextWidths = { ...manualWidths.value };
    delete nextWidths[key];
    manualWidths.value = nextWidths;
    saveWidths();
  }

  function startResize(key: Key, event: MouseEvent) {
    event.preventDefault();
    event.stopPropagation();

    removeResizeListeners?.();

    const startX = event.clientX;
    const startWidth = columnWidths.value[key];
    resizingColumn.value = key;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    const onMouseMove = (moveEvent: MouseEvent) => {
      setColumnWidth(key, startWidth + moveEvent.clientX - startX);
    };

    const onMouseUp = () => {
      resizingColumn.value = null;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      saveWidths();
      removeResizeListeners?.();
      removeResizeListeners = null;
    };

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp, { once: true });

    removeResizeListeners = () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }

  onUnmounted(() => {
    removeResizeListeners?.();
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  });

  return {
    sort,
    sortedRows,
    columnWidths,
    tableMinWidth,
    columnStyle,
    toggleSort,
    getSortIcon,
    startResize,
    resetColumnWidth,
    resizingColumn,
  };
}
