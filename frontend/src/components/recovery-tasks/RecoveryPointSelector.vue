<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  ArrowPathIcon,
  CircleStackIcon,
  ClockIcon,
  MagnifyingGlassIcon,
} from "@heroicons/vue/24/outline";
import type { Repository } from "@/types/repository";
import type { SnapshotInfo } from "@/types/recovery";

const props = defineProps<{
  repositories: Repository[];
  snapshots: SnapshotInfo[];
  selectedRepository: string | number;
  selectedSnapshotId: string;
  snapshotSearchQuery: string;
  snapshotKindFilter: string;
  snapshotTotal: number;
  snapshotsLoading: boolean;
  snapshotsLoadingMore: boolean;
  hasMoreSnapshots: boolean;
  formatBytes: (bytes: number) => string;
  formatDateTime: (value?: string | null) => string;
}>();

const emit = defineEmits<{
  "update:selectedRepository": [value: string | number];
  "update:selectedSnapshotId": [value: string];
  "update:snapshotSearchQuery": [value: string];
  "update:snapshotKindFilter": [value: string];
  loadMore: [];
}>();

const { t } = useI18n();

function snapshotDisplayTime(snapshot: SnapshotInfo): string | undefined {
  return snapshot.snapshot_time || snapshot.created_at;
}

function isNoChangeSnapshot(snapshot: SnapshotInfo): boolean {
  return Boolean(
    snapshot.metadata?.no_changes || snapshot.metadata?.last_no_changes,
  );
}

function snapshotKindLabel(snapshot: SnapshotInfo): string {
  if (isNoChangeSnapshot(snapshot)) return t("recoveryTasks.snapshots.noChange");
  if (Number(snapshot.total_size || snapshot.size_bytes || 0) > 0) {
    return t("recoveryTasks.snapshots.data");
  }
  return t("recoveryTasks.snapshots.empty");
}
</script>

<template>
  <section class="rounded-lg border border-border bg-background-secondary/40 p-4">
    <div class="flex items-start gap-3 mb-4">
      <CircleStackIcon class="w-5 h-5 text-emerald-600 mt-0.5" />
      <div>
        <h3 class="text-sm font-semibold text-foreground">
          {{ t("recoveryTasks.sections.source") }}
        </h3>
        <p class="text-xs text-foreground-secondary mt-1">
          {{ t("recoveryTasks.sections.sourceHelp") }}
        </p>
      </div>
    </div>

    <div>
      <label class="block text-sm font-medium text-foreground-secondary mb-1">
        {{ t("recoveryTasks.form.repository") }}
      </label>
      <select
        :value="props.selectedRepository"
        class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500"
        @change="
          emit(
            'update:selectedRepository',
            ($event.target as HTMLSelectElement).value,
          )
        "
      >
        <option class="bg-background" value="">
          {{ t("common.select") || "Select" }}
        </option>
        <option
          v-for="repo in props.repositories"
          :key="repo.id"
          class="bg-background"
          :value="repo.id"
        >
          {{ repo.name }}
        </option>
      </select>
    </div>

    <div class="mt-4">
      <div class="flex items-center justify-between gap-3 mb-2">
        <label class="block text-sm font-medium text-foreground-secondary">
          {{ t("recoveryTasks.form.snapshot") }}
        </label>
        <span class="text-xs text-foreground-secondary">
          {{ props.snapshots.length }} / {{ props.snapshotTotal }}
        </span>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-[minmax(0,1fr)_170px] gap-2 mb-3">
        <div class="relative">
          <MagnifyingGlassIcon
            class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400"
          />
          <input
            :value="props.snapshotSearchQuery"
            type="text"
            :placeholder="t('recoveryTasks.form.snapshotSearchPlaceholder')"
            class="w-full pl-9 pr-4 py-2 text-sm border border-border rounded-lg bg-background text-foreground placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            @input="
              emit(
                'update:snapshotSearchQuery',
                ($event.target as HTMLInputElement).value,
              )
            "
          />
        </div>
        <select
          :value="props.snapshotKindFilter"
          class="px-3 py-2 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500"
          @change="
            emit(
              'update:snapshotKindFilter',
              ($event.target as HTMLSelectElement).value,
            )
          "
        >
          <option class="bg-background" value="data">
            {{ t("recoveryTasks.snapshotFilters.data") }}
          </option>
          <option class="bg-background" value="no_change">
            {{ t("recoveryTasks.snapshotFilters.noChange") }}
          </option>
          <option class="bg-background" value="all">
            {{ t("recoveryTasks.snapshotFilters.allRecoverable") }}
          </option>
        </select>
      </div>

      <div
        v-if="!props.selectedRepository"
        class="rounded-lg border border-dashed border-border p-8 text-center"
      >
        <CircleStackIcon class="w-8 h-8 text-slate-400 mx-auto mb-3" />
        <p class="text-sm font-medium text-foreground">
          {{ t("recoveryTasks.empty.selectRepositoryTitle") }}
        </p>
        <p class="text-xs text-foreground-secondary mt-1">
          {{ t("recoveryTasks.empty.selectRepositoryDescription") }}
        </p>
      </div>

      <div
        v-else-if="props.snapshotsLoading"
        class="rounded-lg border border-border p-8 flex justify-center bg-card"
      >
        <div
          class="w-7 h-7 border-4 border-emerald-200 border-t-emerald-600 rounded-full animate-spin"
        />
      </div>

      <div
        v-else-if="props.snapshots.length === 0"
        class="rounded-lg border border-dashed border-border p-8 text-center"
      >
        <ClockIcon class="w-8 h-8 text-slate-400 mx-auto mb-3" />
        <p class="text-sm font-medium text-foreground">
          {{ t("recoveryTasks.empty.noSnapshotsTitle") }}
        </p>
        <p class="text-xs text-foreground-secondary mt-1">
          {{ t("recoveryTasks.empty.noSnapshotsDescription") }}
        </p>
      </div>

      <div v-else class="max-h-[360px] overflow-y-auto pr-1 space-y-2">
        <button
          v-for="snap in props.snapshots"
          :key="snap.id"
          type="button"
          :class="[
            'w-full text-left rounded-lg border p-4 transition-colors',
            props.selectedSnapshotId === snap.id
              ? 'border-emerald-500 bg-emerald-50/70 dark:bg-emerald-950/20'
              : 'border-border bg-card hover:bg-hover',
          ]"
          @click="emit('update:selectedSnapshotId', snap.id)"
        >
          <div class="flex items-start justify-between gap-4">
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <span
                  v-if="props.selectedSnapshotId === snap.id"
                  class="w-2 h-2 rounded-full bg-emerald-500"
                />
                <p class="text-sm font-semibold text-foreground truncate">
                  {{ snap.name || snap.id }}
                </p>
              </div>
              <p class="text-xs text-foreground-secondary mt-1 font-mono truncate">
                {{ snap.source_path || snap.id }}
              </p>
            </div>
            <div class="text-right shrink-0">
              <p class="text-sm font-medium text-foreground">
                {{ props.formatBytes(snap.total_size || snap.size_bytes || 0) }}
              </p>
              <p class="text-xs text-foreground-secondary mt-1">
                {{ snap.file_count || snap.files_total || 0 }}
                {{ t("recoveryTasks.progress.files") }}
              </p>
            </div>
          </div>

          <div class="mt-3 grid grid-cols-1 sm:grid-cols-4 gap-2 text-xs text-foreground-secondary">
            <span>{{ props.formatDateTime(snapshotDisplayTime(snap)) }}</span>
            <span class="truncate">{{ snap.task_name || snap.description || "-" }}</span>
            <span
              :class="[
                'inline-flex w-fit items-center rounded-full px-2 py-0.5 text-[11px] font-medium',
                isNoChangeSnapshot(snap)
                  ? 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
                  : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
              ]"
            >
              {{ snapshotKindLabel(snap) }}
            </span>
            <span class="font-mono truncate">{{ snap.id }}</span>
          </div>
        </button>

        <button
          v-if="props.hasMoreSnapshots"
          type="button"
          :disabled="props.snapshotsLoadingMore"
          class="w-full inline-flex items-center justify-center gap-2 px-3 py-2 text-sm border border-border rounded-lg hover:bg-hover disabled:opacity-60"
          @click="emit('loadMore')"
        >
          <ArrowPathIcon
            :class="[
              'w-4 h-4',
              props.snapshotsLoadingMore ? 'animate-spin' : '',
            ]"
          />
          {{ t("recoveryTasks.snapshots.loadMore") }}
        </button>
      </div>
    </div>
  </section>
</template>
