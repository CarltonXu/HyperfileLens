<script setup lang="ts">
import { useI18n } from "vue-i18n";
import type { Component } from "vue";
import type { Repository } from "@/types/repository";
import {
  CheckCircleIcon,
  CircleStackIcon,
  Cog6ToothIcon,
  ExclamationCircleIcon,
  FolderIcon,
  KeyIcon,
  LinkIcon,
  PencilIcon,
  PlayIcon,
  ServerIcon,
  SignalIcon,
  SparklesIcon,
  TrashIcon,
} from "@heroicons/vue/24/outline";
import { GlobeAltIcon } from "@heroicons/vue/24/solid";

defineProps<{
  loading: boolean;
  filteredCount: number;
  repositories: Repository[];
  testingConnection: string | null;
  connectionTestResult: Record<
    string,
    { success: boolean; message: string; details?: any }
  >;
  getRepoTypeColor: (type: string) => string;
  getRepoTypeIcon: (type: string) => Component;
  getRepoTypeLabel: (type: string | undefined | null) => string;
  getNodeName: (nodeId: string | null | undefined) => string;
  getProgressColor: (quotaStatus: string) => string;
  formatBytes: (bytes: number) => string;
}>();

const emit = defineEmits<{
  initKopia: [repo: Repository];
  saveKopiaPassword: [repo: Repository];
  testConnection: [repo: Repository];
  edit: [repo: Repository];
  detail: [repo: Repository];
  analyze: [repo: Repository];
  delete: [repo: Repository];
}>();

const { t } = useI18n();
</script>

<template>
  <template v-if="loading">
    <div class="flex items-center justify-center py-12">
      <div
        class="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"
      />
    </div>
  </template>

  <div
    v-else-if="filteredCount === 0"
    class="bg-background-secondary rounded-xl border border-border p-12 text-center"
  >
    <div
      class="w-16 h-16 bg-background-tertiary/50 rounded-full flex items-center justify-center mx-auto mb-4"
    >
      <CircleStackIcon class="w-8 h-8 text-foreground-muted" />
    </div>
    <h3 class="text-lg font-medium text-foreground mb-1">
      {{ t("repository.empty.title") }}
    </h3>
    <p class="text-foreground-secondary">
      {{ t("repository.empty.description") }}
    </p>
  </div>

  <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    <div
      v-for="repo in repositories"
      :key="repo.id"
      class="rounded-xl border border-border p-5 shadow-sm hover:shadow-md transition-shadow"
    >
      <div class="flex items-start justify-between mb-3">
        <div
          :class="[
            'w-10 h-10 rounded-lg flex items-center justify-center',
            getRepoTypeColor(repo.repo_type),
          ]"
        >
          <component :is="getRepoTypeIcon(repo.repo_type)" class="w-5 h-5" />
        </div>
        <div class="flex items-center gap-2">
          <span
            v-if="repo.kopia_initialized"
            class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700"
          >
            <CheckCircleIcon class="w-3 h-3" />
            Kopia
          </span>
          <span
            :class="[
              'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
              repo.status === 'active'
                ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 dark:text-emerald-400'
                : 'bg-background-tertiary/50 text-foreground-secondary',
            ]"
          >
            {{
              repo.status === "active"
                ? t("common.active")
                : t("common.inactive")
            }}
          </span>
        </div>
      </div>

      <h3 class="text-base font-semibold text-white-800 mb-1">
        {{ repo.name }}
      </h3>
      <p class="text-sm text-foreground-secondary mb-3">
        {{ repo.description || getRepoTypeLabel(repo.repo_type) }}
      </p>

      <div class="rounded-lg p-3 mb-3 space-y-2">
        <template v-if="repo.repo_type === 's3'">
          <div class="flex items-center gap-2 text-sm">
            <GlobeAltIcon class="w-4 h-4 text-foreground-muted flex-shrink-0" />
            <span
              class="text-foreground-secondary truncate"
              :title="repo.config?.endpoint"
            >
              {{ repo.config?.endpoint || "-" }}
            </span>
          </div>
          <div class="flex items-center gap-2 text-sm">
            <FolderIcon class="w-4 h-4 text-foreground-muted flex-shrink-0" />
            <span class="text-foreground-secondary">
              {{ repo.config?.bucket || "-" }}
            </span>
            <span v-if="repo.config?.prefix" class="text-foreground-muted">
              /{{ repo.config?.prefix }}
            </span>
          </div>
        </template>

        <template v-else-if="repo.repo_type === 'nas'">
          <div class="flex items-center gap-2 text-sm">
            <ServerIcon class="w-4 h-4 text-foreground-muted flex-shrink-0" />
            <span class="text-foreground-secondary">
              {{ repo.config?.server || "-" }}
            </span>
          </div>
          <div class="flex items-center gap-2 text-sm">
            <FolderIcon class="w-4 h-4 text-foreground-muted flex-shrink-0" />
            <span class="text-foreground-secondary">
              {{ repo.config?.export_path || "-" }}
            </span>
          </div>
          <div class="flex items-center gap-2 text-sm">
            <span
              class="text-xs text-foreground-muted uppercase px-1.5 py-0.5 bg-slate-200 dark:bg-slate-600 rounded"
            >
              {{ repo.config?.nas_type?.toUpperCase() || "NFS" }}
            </span>
          </div>
        </template>

        <template v-else-if="repo.repo_type === 'local'">
          <div class="flex items-center gap-2 text-sm">
            <FolderIcon class="w-4 h-4 text-foreground-muted flex-shrink-0" />
            <span
              class="text-foreground-secondary truncate"
              :title="repo.config?.path"
            >
              {{ repo.config?.path || "-" }}
            </span>
          </div>
        </template>

        <div
          class="flex items-center gap-2 text-sm pt-2 border-t border-border"
        >
          <LinkIcon class="w-4 h-4 text-foreground-muted flex-shrink-0" />
          <span class="text-foreground-secondary">
            {{ getNodeName(repo.bound_node) }}
          </span>
        </div>
      </div>

      <div class="mb-4">
        <div
          class="flex items-center justify-between text-xs text-foreground-secondary mb-1"
        >
          <span>{{ t("repository.stats.usedSpace") }}</span>
          <span>
            {{ formatBytes(repo.used_space || 0) }} /
            {{ formatBytes(repo.capacity || 0) }}
          </span>
        </div>
        <div
          class="h-2 bg-background-tertiary/50 rounded-full overflow-hidden relative"
        >
          <div
            v-if="repo.quota_enabled && (repo.quota_bytes || 0) > 0"
            class="h-full absolute left-0 bg-slate-300 dark:bg-slate-600/50 dark:bg-slate-600/50 opacity-50 rounded-full transition-all"
            :style="{
              width: `${Math.min(((repo.quota_bytes || 0) / (repo.capacity || 1)) * 100, 100)}%`,
            }"
          />
          <div
            class="h-full rounded-full transition-all relative"
            :class="getProgressColor(repo.quota_status || 'unlimited')"
            :style="{
              width: `${repo.capacity ? ((repo.used_space || 0) / repo.capacity) * 100 : 0}%`,
            }"
          />
        </div>
        <div
          v-if="repo.quota_enabled && (repo.quota_bytes || 0) > 0"
          class="mt-2 flex items-center justify-between text-xs"
        >
          <div class="flex items-center gap-1">
            <ExclamationCircleIcon
              v-if="
                repo.quota_status === 'warning' ||
                repo.quota_status === 'critical'
              "
              :class="[
                'w-3.5 h-3.5',
                repo.quota_status === 'critical'
                  ? 'text-red-500 dark:text-red-400'
                  : 'text-amber-500 dark:text-amber-400',
              ]"
            />
            <span class="text-foreground-secondary">
              {{ t("repository.stats.quota") }}:
              {{ repo.quota_bytes_formatted }}
            </span>
          </div>
          <span
            :class="[
              'text-xs font-medium',
              repo.quota_status === 'critical'
                ? 'text-red-500 dark:text-red-400'
                : repo.quota_status === 'warning'
                  ? 'text-amber-500 dark:text-amber-400'
                  : 'text-foreground-secondary',
            ]"
          >
            {{ repo.quota_usage_percentage?.toFixed(1) || 0 }}%
          </span>
        </div>
        <div
          v-else-if="repo.quota_enabled"
          class="mt-2 flex items-center justify-between text-xs text-foreground-muted"
        >
          <span>
            {{ t("repository.stats.quota") }}:
            {{ t("repository.stats.unlimited") }}
          </span>
        </div>
      </div>

      <div
        class="flex items-center justify-between pt-3 border-t border-border"
      >
        <span class="text-xs text-foreground-muted uppercase">
          {{ getRepoTypeLabel(repo.repo_type) }}
        </span>
        <div class="flex items-center gap-1">
          <button
            v-if="!repo.kopia_initialized && repo.bound_node"
            @click="emit('initKopia', repo)"
            class="p-1.5 text-blue-500 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
            :title="t('repository.initKopia')"
          >
            <PlayIcon class="w-4 h-4" />
          </button>
          <button
            v-if="repo.kopia_initialized"
            @click="emit('saveKopiaPassword', repo)"
            class="p-1.5 text-foreground-muted hover:text-amber-600 dark:hover:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/30 rounded-lg transition-colors"
            :title="t('repository.saveKopiaPassword')"
          >
            <KeyIcon class="w-4 h-4" />
          </button>
          <button
            @click="emit('testConnection', repo)"
            :disabled="testingConnection === repo.id"
            :class="[
              'p-1.5 rounded-lg transition-colors',
              testingConnection === repo.id
                ? 'text-slate-300 cursor-wait'
                : connectionTestResult[repo.id]?.success
                  ? 'text-emerald-500 hover:text-emerald-700 dark:hover:text-emerald-300 hover:bg-emerald-50 dark:hover:bg-emerald-900/30'
                  : 'text-foreground-muted hover:text-foreground-secondary hover:bg-background-tertiary/50',
            ]"
            :title="
              testingConnection === repo.id
                ? t('repository.testing')
                : t('repository.testConnection')
            "
          >
            <SignalIcon
              v-if="testingConnection === repo.id"
              class="w-4 h-4 animate-pulse"
            />
            <CheckCircleIcon
              v-else-if="connectionTestResult[repo.id]?.success"
              class="w-4 h-4"
            />
            <LinkIcon v-else class="w-4 h-4" />
          </button>
          <button
            @click="emit('analyze', repo)"
            class="p-1.5 text-foreground-muted hover:text-violet-600 hover:bg-violet-50 dark:hover:bg-violet-900/30 rounded-lg transition-colors"
            :title="t('aiInsights.title')"
          >
            <SparklesIcon class="w-4 h-4" />
          </button>
          <button
            @click="emit('edit', repo)"
            class="p-1.5 text-foreground-muted hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
            :title="t('common.edit')"
          >
            <PencilIcon class="w-4 h-4" />
          </button>
          <button
            @click="emit('detail', repo)"
            class="p-1.5 text-foreground-muted hover:text-foreground-secondary hover:bg-background-tertiary/50 rounded-lg transition-colors"
            :title="t('common.details')"
          >
            <Cog6ToothIcon class="w-4 h-4" />
          </button>
          <button
            @click="emit('delete', repo)"
            class="p-1.5 text-foreground-muted hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors"
            :title="t('common.delete')"
          >
            <TrashIcon class="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
