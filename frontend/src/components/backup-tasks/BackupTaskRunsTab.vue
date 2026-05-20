<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { ListBulletIcon } from "@heroicons/vue/24/outline";

defineProps<{
  runs: any[];
  loading: boolean;
  getStatusColor: (status: string) => string;
  formatDateTime: (value?: string | null) => string;
  runDuration: (run: any) => string;
}>();

const { t } = useI18n();
</script>

<template>
  <div class="space-y-3">
    <div v-if="loading" class="py-10 text-center text-foreground-secondary">
      {{ t("common.loading") }}
    </div>
    <div
      v-else-if="runs.length === 0"
      class="rounded-xl border border-dashed border-border bg-background/50 px-6 py-12 text-center"
    >
      <div
        class="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-violet-50 text-violet-600 dark:bg-violet-950/30 dark:text-violet-300"
      >
        <ListBulletIcon class="h-7 w-7" />
      </div>
      <h3 class="mt-4 text-sm font-semibold text-foreground">
        {{ t("backupTasks.emptyStates.runsTitle") }}
      </h3>
      <p
        class="mx-auto mt-2 max-w-md text-sm leading-6 text-foreground-secondary"
      >
        {{ t("backupTasks.emptyStates.runsDesc") }}
      </p>
    </div>
    <div v-else class="space-y-2">
      <div
        v-for="run in runs"
        :key="run.id"
        class="rounded-lg border border-border bg-card px-3 py-2.5 transition-colors hover:bg-hover"
      >
        <div class="flex flex-col gap-2">
          <div class="flex items-start justify-between gap-3">
            <div class="flex min-w-0 items-start gap-2.5">
              <span
                class="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-background-secondary text-foreground-muted"
              >
                <ListBulletIcon class="h-4 w-4" />
              </span>
              <div class="min-w-0">
                <p class="truncate text-sm font-medium text-foreground">
                  {{ run.name }}
                </p>
                <p class="mt-0.5 truncate text-xs text-foreground-secondary">
                  {{ formatDateTime(run.created_at) }}
                  <span v-if="run.proxy_name"> · {{ run.proxy_name }}</span>
                </p>
                <p
                  v-if="run.message || run.error_message"
                  class="mt-1 truncate text-xs text-foreground-secondary"
                >
                  {{ run.message || run.error_message }}
                </p>
              </div>
            </div>
            <span
              :class="[
                'inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-[11px] font-medium',
                getStatusColor(run.status),
              ]"
            >
              {{ t(`backupTasks.status.${run.status}`) }}
            </span>
          </div>

          <div
            class="grid grid-cols-2 gap-2 text-xs md:grid-cols-[65px_80px_70px_1fr_85px]"
          >
            <div>
              <p class="text-[11px] text-foreground-muted">
                {{ t("backupTasks.progress.progress") }}
              </p>
              <p class="font-medium text-foreground">
                {{ run.progress || 0 }}%
              </p>
            </div>
            <div>
              <p class="text-[11px] text-foreground-muted">
                {{ t("alertsCenter.common.duration") }}
              </p>
              <p class="font-medium text-foreground">
                {{ runDuration(run) }}
              </p>
            </div>
            <div>
              <p class="text-[11px] text-foreground-muted">
                {{ t("backupTasks.progress.eta") }}
              </p>
              <p class="font-medium text-foreground">
                {{ run.eta || "-" }}
              </p>
            </div>
            <div>
              <p class="text-[11px] text-foreground-muted">
                {{ t("backupTasks.progress.files") }}
              </p>
              <p class="font-medium text-foreground">
                {{ run.processed_files || 0 }} / {{ run.total_files || 0 }}
              </p>
            </div>
            <div>
              <p class="text-[11px] text-foreground-muted">
                {{ t("backupTasks.progress.speed") }}
              </p>
              <p class="font-medium text-foreground">
                {{ run.speed_mbps ? `${run.speed_mbps.toFixed(2)} MB/s` : "-" }}
              </p>
            </div>
          </div>

          <div
            class="h-1.5 overflow-hidden rounded-full bg-background-tertiary"
          >
            <div
              class="h-full bg-primary transition-all"
              :style="{ width: `${Math.min(run.progress || 0, 100)}%` }"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
