<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { CircleStackIcon } from "@heroicons/vue/24/outline";
import {
  isNoChangeSnapshotReference,
  snapshotDisplayFileCount,
  snapshotDisplaySize,
  snapshotDisplayTime,
  snapshotReferencedId,
  snapshotStatusClass,
} from "@/features/backup-tasks/snapshotDisplay";

const props = defineProps<{
  tooltip: {
    snapshot: any;
    top: number;
    left: number;
    placement: "top" | "bottom";
  } | null;
  formatDateTime: (value?: string | null) => string;
  formatBytes: (value: number) => string;
}>();

defineEmits<{
  mouseenter: [];
  mouseleave: [];
}>();

const { t } = useI18n();

function snapshotStatusLabel(snapshot: any) {
  const status = snapshot?.snapshot_status || "available";
  return t(`backupTasks.detail.snapshotStatuses.${status}`);
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="props.tooltip"
      class="fixed z-[2147483647] w-72 -translate-x-1/2 rounded-lg border border-border bg-card p-3 text-xs shadow-2xl pointer-events-auto"
      :class="props.tooltip.placement === 'top' ? '-translate-y-full' : ''"
      :style="{
        top: `${props.tooltip.top}px`,
        left: `${props.tooltip.left}px`,
      }"
      @mouseenter="$emit('mouseenter')"
      @mouseleave="$emit('mouseleave')"
    >
      <div class="flex items-center gap-2 border-b border-border pb-2">
        <CircleStackIcon class="w-4 h-4 text-emerald-600" />
        <p class="font-semibold text-foreground truncate">
          {{
            props.tooltip.snapshot.name ||
            props.tooltip.snapshot.version ||
            props.tooltip.snapshot.id
          }}
        </p>
      </div>
      <dl class="mt-2 grid grid-cols-[88px_minmax(0,1fr)] gap-x-2 gap-y-1.5">
        <dt class="text-foreground-muted">
          {{ t("backupTasks.detail.snapshotId") }}
        </dt>
        <dd class="text-foreground truncate">
          {{ props.tooltip.snapshot.version || props.tooltip.snapshot.id }}
        </dd>
        <dt class="text-foreground-muted">
          {{ t("common.date") }}
        </dt>
        <dd class="text-foreground">
          {{ props.formatDateTime(snapshotDisplayTime(props.tooltip.snapshot)) }}
        </dd>
        <dt class="text-foreground-muted">
          {{
            isNoChangeSnapshotReference(props.tooltip.snapshot)
              ? t("backupTasks.detail.dataWritten")
              : t("backupTasks.progress.size")
          }}
        </dt>
        <dd class="text-foreground">
          {{ props.formatBytes(snapshotDisplaySize(props.tooltip.snapshot)) }}
        </dd>
        <dt class="text-foreground-muted">
          {{ t("backupTasks.progress.files") }}
        </dt>
        <dd class="text-foreground">
          {{
            isNoChangeSnapshotReference(props.tooltip.snapshot)
              ? t("backupTasks.detail.changedFiles", { count: 0 })
              : snapshotDisplayFileCount(props.tooltip.snapshot)
          }}
        </dd>
        <dt class="text-foreground-muted">
          {{ t("backupTasks.detail.kopiaState") }}
        </dt>
        <dd>
          <span
            :class="[
              'rounded-full px-1.5 py-0.5 text-[10px] font-medium',
              snapshotStatusClass(props.tooltip.snapshot),
            ]"
          >
            {{ snapshotStatusLabel(props.tooltip.snapshot) }}
          </span>
        </dd>
        <template v-if="isNoChangeSnapshotReference(props.tooltip.snapshot)">
          <dt class="text-foreground-muted">
            {{ t("common.status") }}
          </dt>
          <dd class="text-amber-600 dark:text-amber-300">
            {{ t("backupTasks.detail.noChanges") }}
          </dd>
          <dt class="text-foreground-muted">
            {{ t("backupTasks.detail.referencedSnapshot") }}
          </dt>
          <dd class="text-foreground truncate">
            {{ snapshotReferencedId(props.tooltip.snapshot) || "-" }}
          </dd>
          <dt class="text-foreground-muted">
            {{ t("backupTasks.detail.referencedSize") }}
          </dt>
          <dd class="text-foreground">
            {{ props.formatBytes(props.tooltip.snapshot.total_size || 0) }}
          </dd>
          <dt class="text-foreground-muted">
            {{ t("backupTasks.detail.referencedFiles") }}
          </dt>
          <dd class="text-foreground">
            {{ props.tooltip.snapshot.file_count || 0 }}
          </dd>
        </template>
        <dt v-if="props.tooltip.snapshot.expires_at" class="text-foreground-muted">
          {{ t("backupTasks.detail.expiresAt") }}
        </dt>
        <dd v-if="props.tooltip.snapshot.expires_at" class="text-foreground">
          {{ props.formatDateTime(props.tooltip.snapshot.expires_at) }}
        </dd>
      </dl>
    </div>
  </Teleport>
</template>
