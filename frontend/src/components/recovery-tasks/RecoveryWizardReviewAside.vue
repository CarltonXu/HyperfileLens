<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { CircleStackIcon } from "@heroicons/vue/24/outline";
import type { ProxyNode } from "@/types/proxy";
import type { RecoveryTaskCreateData, SnapshotInfo } from "@/types/recovery";

defineProps<{
  recovery: RecoveryTaskCreateData;
  selectedSnapshot?: SnapshotInfo;
  selectedTargetNode?: ProxyNode;
  selectedFileStats: {
    paths: number;
    knownFiles: number;
    knownBytes: number;
  };
  formatBytes: (bytes: number) => string;
}>();

const { t } = useI18n();
</script>

<template>
  <aside class="rounded-lg border border-border bg-card p-4 h-fit sticky top-20">
    <div class="flex items-center gap-2 mb-4">
      <CircleStackIcon class="w-5 h-5 text-emerald-600" />
      <h3 class="text-sm font-semibold text-foreground">
        {{ t("recoveryTasks.review.title") }}
      </h3>
    </div>
    <dl class="space-y-3 text-sm">
      <div>
        <dt class="text-xs text-foreground-secondary">
          {{ t("recoveryTasks.form.snapshot") }}
        </dt>
        <dd class="font-medium text-foreground break-all">
          {{ selectedSnapshot?.name || selectedSnapshot?.id || "-" }}
        </dd>
      </div>
      <div class="grid grid-cols-2 gap-3">
        <div>
          <dt class="text-xs text-foreground-secondary">
            {{ t("recoveryTasks.progress.size") }}
          </dt>
          <dd class="font-medium text-foreground">
            {{
              formatBytes(
                selectedSnapshot?.total_size ||
                  selectedSnapshot?.size_bytes ||
                  0,
              )
            }}
          </dd>
        </div>
        <div>
          <dt class="text-xs text-foreground-secondary">
            {{ t("recoveryTasks.progress.files") }}
          </dt>
          <dd class="font-medium text-foreground">
            {{ selectedSnapshot?.file_count || selectedSnapshot?.files_total || 0 }}
          </dd>
        </div>
      </div>
      <div>
        <dt class="text-xs text-foreground-secondary">
          {{ t("recoveryTasks.scope.title") }}
        </dt>
        <dd class="font-medium text-foreground">
          {{
            recovery.restore_scope === "selected_paths"
              ? `${selectedFileStats.paths} ${t("recoveryTasks.scope.selectedCount")}`
              : t("recoveryTasks.scope.entire")
          }}
        </dd>
      </div>
      <div v-if="recovery.restore_scope === 'selected_paths'">
        <dt class="text-xs text-foreground-secondary">
          {{ t("recoveryTasks.review.knownSelection") }}
        </dt>
        <dd class="font-medium text-foreground">
          {{ selectedFileStats.knownFiles }}
          {{ t("recoveryTasks.progress.files") }} ·
          {{ formatBytes(selectedFileStats.knownBytes) }}
        </dd>
      </div>
      <div>
        <dt class="text-xs text-foreground-secondary">
          {{ t("recoveryTasks.review.sourcePath") }}
        </dt>
        <dd class="font-mono text-xs text-foreground break-all">
          {{ selectedSnapshot?.source_path || "-" }}
        </dd>
      </div>
      <div>
        <dt class="text-xs text-foreground-secondary">
          {{ t("recoveryTasks.form.targetNode") }}
        </dt>
        <dd class="font-medium text-foreground">
          {{ selectedTargetNode?.name || "-" }}
        </dd>
      </div>
      <div>
        <dt class="text-xs text-foreground-secondary">
          {{ t("recoveryTasks.form.targetPath") }}
        </dt>
        <dd class="font-mono text-xs text-foreground break-all">
          {{ recovery.target_path || "-" }}
        </dd>
      </div>
      <div>
        <dt class="text-xs text-foreground-secondary">
          {{ t("recoveryTasks.form.conflictPolicy") }}
        </dt>
        <dd class="font-medium text-foreground">
          {{ t(`recoveryTasks.conflict.${recovery.conflict_policy || "skip"}`) }}
        </dd>
      </div>
    </dl>
  </aside>
</template>
