<script setup lang="ts">
import { useI18n } from "vue-i18n";
import type { Component } from "vue";
import type { Repository } from "@/types/repository";
import type { ProxyNode } from "@/types/proxy";
import {
  CheckCircleIcon,
  FolderIcon,
  ServerIcon,
} from "@heroicons/vue/24/outline";
import { GlobeAltIcon } from "@heroicons/vue/24/solid";

defineProps<{
  repository: Repository;
  getRepoTypeColor: (type: string) => string;
  getRepoTypeIcon: (type: string) => Component;
  getRepoTypeLabel: (type: string | undefined | null) => string;
  getProgressColor: (quotaStatus: string) => string;
  getNodeName: (nodeId: string | null | undefined) => string;
  getNode: (nodeId: string | null | undefined) => ProxyNode | undefined;
  getNodeStatus: (nodeId: string | null | undefined) => string;
  formatBytes: (bytes: number) => string;
}>();

const emit = defineEmits<{
  close: [];
}>();

const { t } = useI18n();
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/50" @click="emit('close')" />
      <div
        class="relative modal-surface rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
      >
        <div
          class="px-6 py-4 border-b border-border flex items-center justify-between sticky top-0 modal-surface z-10"
        >
          <h2 class="text-lg font-semibold text-foreground">
            {{ repository.name }}
          </h2>
          <button
            @click="emit('close')"
            class="p-1 hover:bg-background-tertiary/50 rounded-lg"
          >
            <svg
              class="w-5 h-5 text-foreground-muted"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
        <div class="p-6 space-y-4">
          <div class="flex items-center gap-3">
            <div
              :class="[
                'w-12 h-12 rounded-lg flex items-center justify-center',
                getRepoTypeColor(repository.repo_type),
              ]"
            >
              <component
                :is="getRepoTypeIcon(repository.repo_type)"
                class="w-6 h-6"
              />
            </div>
            <div class="flex-1">
              <p class="font-medium text-foreground dark:text-slate-200">
                {{ getRepoTypeLabel(repository.repo_type) }}
              </p>
              <p class="text-sm text-foreground-secondary">
                {{
                  repository.status === "active"
                    ? t("common.active")
                    : t("common.inactive")
                }}
              </p>
            </div>
            <span
              v-if="repository.kopia_initialized"
              class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-700"
            >
              <CheckCircleIcon class="w-4 h-4" />
              Kopia {{ t("repository.initialized") }}
            </span>
          </div>

          <div v-if="repository.description" class="rounded-lg p-4">
            <p class="text-xs text-foreground-secondary mb-1">
              {{ t("common.description") }}
            </p>
            <p class="text-sm text-foreground dark:text-slate-200">
              {{ repository.description }}
            </p>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div class="bg-background-secondary rounded-lg p-4">
              <p class="text-xs text-foreground-secondary">
                {{ t("repository.stats.totalCapacity") }}
              </p>
              <p class="font-semibold text-slate-800 text-lg">
                {{ formatBytes(repository.capacity || 0) }}
              </p>
            </div>
            <div class="bg-background-secondary rounded-lg p-4">
              <p class="text-xs text-foreground-secondary">
                {{ t("repository.stats.usedSpace") }}
              </p>
              <p class="font-semibold text-slate-800 text-lg">
                {{ formatBytes(repository.used_space || 0) }}
              </p>
            </div>
          </div>

          <div
            v-if="
              repository.quota_enabled ||
              (repository.quota_bytes && repository.quota_bytes > 0)
            "
            class="bg-background-secondary rounded-lg p-4 space-y-3"
          >
            <div class="flex items-center justify-between">
              <h4
                class="font-medium text-foreground dark:text-slate-200 flex items-center gap-2"
              >
                <div
                  class="w-5 h-5 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center"
                >
                  <svg
                    class="w-3 h-3 text-white"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                    />
                  </svg>
                </div>
                {{ t("repository.stats.quota") }}
              </h4>
              <span
                v-if="!repository.quota_enabled"
                class="text-xs px-2 py-1 rounded-full bg-slate-200 dark:bg-slate-600 dark:bg-slate-600 text-foreground-secondary"
              >
                {{ t("repository.stats.disabled") }}
              </span>
              <span
                v-else
                class="text-xs px-2 py-1 rounded-full"
                :class="{
                  'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 dark:text-emerald-400':
                    repository.quota_status === 'ok',
                  'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400':
                    repository.quota_status === 'warning',
                  'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400':
                    repository.quota_status === 'critical',
                }"
              >
                {{
                  repository.quota_status === "ok"
                    ? t("common.statusValues.normal")
                    : repository.quota_status === "warning"
                      ? t("common.statusValues.warning")
                      : repository.quota_status === "critical"
                        ? t("common.statusValues.critical")
                        : ""
                }}
              </span>
            </div>

            <div
              v-if="
                repository.quota_enabled && (repository.quota_bytes || 0) > 0
              "
              class="space-y-2"
            >
              <div class="flex items-center justify-between text-xs">
                <span class="text-foreground-secondary">
                  {{ t("repository.stats.usage") }}
                </span>
                <span
                  class="font-medium"
                  :class="{
                    'text-emerald-600 dark:text-emerald-400':
                      repository.quota_status === 'ok',
                    'text-amber-600 dark:text-amber-400':
                      repository.quota_status === 'warning',
                    'text-red-600 dark:text-red-400':
                      repository.quota_status === 'critical',
                  }"
                >
                  {{ repository.quota_usage_percentage?.toFixed(1) || 0 }}%
                </span>
              </div>
              <div
                class="h-3 bg-slate-200 dark:bg-slate-600 dark:bg-slate-600 rounded-full overflow-hidden relative"
              >
                <div
                  class="absolute left-0 top-0 h-full bg-purple-200 dark:bg-purple-900/30 opacity-50"
                  :style="{
                    width: `${Math.min(((repository.quota_bytes || 0) / (repository.capacity || repository.quota_bytes || 1)) * 100, 100)}%`,
                  }"
                ></div>
                <div
                  class="h-full rounded-full relative"
                  :class="
                    getProgressColor(repository.quota_status || 'unlimited')
                  "
                  :style="{
                    width: `${repository.capacity ? ((repository.used_space || 0) / repository.capacity) * 100 : 0}%`,
                  }"
                ></div>
              </div>
              <div class="flex items-center gap-4 text-xs">
                <div class="flex items-center gap-1">
                  <div
                    class="w-3 h-3 rounded bg-purple-200 dark:bg-purple-900/30"
                  ></div>
                  <span class="text-foreground-secondary">
                    {{ t("repository.stats.quotaLimit") }}
                  </span>
                </div>
                <div class="flex items-center gap-1">
                  <div
                    :class="[
                      'w-3 h-3 rounded',
                      getProgressColor(repository.quota_status || 'unlimited'),
                    ]"
                  ></div>
                  <span class="text-foreground-secondary">
                    {{ t("repository.stats.usage") }}
                  </span>
                </div>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-3 text-sm">
              <div>
                <p class="text-xs text-foreground-secondary">
                  {{ t("repository.form.storageQuota") }}
                </p>
                <p class="font-medium text-foreground dark:text-slate-200">
                  {{
                    repository.quota_bytes_formatted ||
                    t("repository.stats.unlimited")
                  }}
                </p>
              </div>
              <div>
                <p class="text-xs text-foreground-secondary">
                  {{ t("repository.form.quotaThreshold") }}
                </p>
                <p class="font-medium text-foreground dark:text-slate-200">
                  {{ repository.quota_warning_threshold || 80 }}%
                </p>
              </div>
            </div>
          </div>

          <div
            v-if="repository.repo_type === 's3'"
            class="bg-background-secondary rounded-lg p-4 space-y-3"
          >
            <h4
              class="font-medium text-foreground dark:text-slate-200 flex items-center gap-2"
            >
              <GlobeAltIcon class="w-5 h-5" />
              {{ t("repository.types.s3") }} {{ t("repository.configInfo") }}
            </h4>
            <div class="grid grid-cols-2 gap-3 text-sm">
              <div>
                <p class="text-xs text-foreground-secondary">
                  {{ t("repository.s3.endpoint") }}
                </p>
                <p class="text-foreground dark:text-slate-200 font-mono">
                  {{ repository.config?.endpoint || "-" }}
                </p>
              </div>
              <div>
                <p class="text-xs text-foreground-secondary">
                  {{ t("repository.s3.bucket") }}
                </p>
                <p class="text-foreground dark:text-slate-200">
                  {{ repository.config?.bucket || "-" }}
                </p>
              </div>
              <div>
                <p class="text-xs text-foreground-secondary">
                  {{ t("repository.s3.region") }}
                </p>
                <p class="text-foreground dark:text-slate-200">
                  {{ repository.config?.region || "-" }}
                </p>
              </div>
              <div>
                <p class="text-xs text-foreground-secondary">
                  {{ t("repository.s3.prefix") }}
                </p>
                <p class="text-foreground dark:text-slate-200">
                  {{ repository.config?.prefix || "-" }}
                </p>
              </div>
              <div>
                <p class="text-xs text-foreground-secondary">
                  {{ t("repository.s3.accessKey") }}
                </p>
                <p class="text-foreground dark:text-slate-200 font-mono">
                  {{ repository.credentials_masked?.access_key || "-" }}
                </p>
              </div>
              <div>
                <p class="text-xs text-foreground-secondary">
                  {{ t("repository.s3.useTLS") }}
                </p>
                <p class="text-foreground dark:text-slate-200">
                  {{
                    repository.config?.use_tls !== false
                      ? t("common.yes")
                      : t("common.no")
                  }}
                </p>
              </div>
            </div>
          </div>

          <div
            v-if="repository.repo_type === 'nas'"
            class="bg-background-secondary rounded-lg p-4 space-y-3"
          >
            <h4
              class="font-medium text-foreground dark:text-slate-200 flex items-center gap-2"
            >
              <ServerIcon class="w-5 h-5" />
              {{ t("repository.types.nas") }} {{ t("repository.configInfo") }}
            </h4>
            <div class="grid grid-cols-2 gap-3 text-sm">
              <div>
                <p class="text-xs text-foreground-secondary">
                  {{ t("repository.nas.server") }}
                </p>
                <p class="text-foreground dark:text-slate-200">
                  {{ repository.config?.server || "-" }}
                </p>
              </div>
              <div>
                <p class="text-xs text-foreground-secondary">
                  {{ t("repository.nas.exportPath") }}
                </p>
                <p class="text-foreground dark:text-slate-200">
                  {{ repository.config?.export_path || "-" }}
                </p>
              </div>
              <div>
                <p class="text-xs text-foreground-secondary">
                  {{ t("repository.nas.nasType") }}
                </p>
                <p class="text-foreground dark:text-slate-200">
                  {{ repository.config?.nas_type?.toUpperCase() || "NFS" }}
                </p>
              </div>
              <div>
                <p class="text-xs text-foreground-secondary">
                  {{ t("repository.nas.mountOptions") }}
                </p>
                <p
                  class="text-foreground dark:text-slate-200 font-mono text-xs"
                >
                  {{ repository.config?.mount_options || "-" }}
                </p>
              </div>
              <div v-if="repository.config?.nas_type === 'cifs'">
                <p class="text-xs text-foreground-secondary">
                  {{ t("repository.nas.username") }}
                </p>
                <p class="text-foreground dark:text-slate-200">
                  {{ repository.config?.username || "-" }}
                </p>
              </div>
            </div>
          </div>

          <div
            v-if="repository.repo_type === 'local'"
            class="bg-background-secondary rounded-lg p-4 space-y-3"
          >
            <h4
              class="font-medium text-foreground dark:text-slate-200 flex items-center gap-2"
            >
              <FolderIcon class="w-5 h-5" />
              {{ t("repository.types.local") }} {{ t("repository.configInfo") }}
            </h4>
            <div class="text-sm">
              <p class="text-xs text-foreground-secondary">
                {{ t("repository.local.path") }}
              </p>
              <p class="text-foreground dark:text-slate-200 font-mono">
                {{ repository.config?.path || "-" }}
              </p>
            </div>
          </div>

          <div class="bg-background-secondary rounded-lg p-4">
            <p class="text-xs text-foreground-secondary mb-1">
              {{ t("sourceResources.boundNode") }}
            </p>
            <div class="flex items-center gap-2">
              <div
                :class="[
                  'w-2 h-2 rounded-full',
                  getNodeStatus(repository.bound_node) === 'online'
                    ? 'bg-emerald-500'
                    : 'bg-slate-300 dark:bg-slate-600/50',
                ]"
              />
              <span class="text-sm text-foreground dark:text-slate-200">
                {{ getNodeName(repository.bound_node) }}
              </span>
              <span
                v-if="getNode(repository.bound_node)?.role"
                class="text-xs text-foreground-muted"
              >
                ({{ getNode(repository.bound_node)?.role }})
              </span>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p class="text-xs text-foreground-secondary">
                {{ t("common.createdAt") }}
              </p>
              <p class="text-foreground dark:text-slate-200">
                {{ new Date(repository.created_at).toLocaleString() }}
              </p>
            </div>
            <div>
              <p class="text-xs text-foreground-secondary">
                {{ t("common.updatedAt") }}
              </p>
              <p class="text-foreground dark:text-slate-200">
                {{
                  repository.updated_at
                    ? new Date(repository.updated_at).toLocaleString()
                    : "-"
                }}
              </p>
            </div>
          </div>
        </div>
        <div
          class="px-6 py-4 border-t border-border flex justify-end sticky bottom-0 modal-surface"
        >
          <button
            @click="emit('close')"
            class="px-4 py-2 text-sm text-foreground-secondary border border-border rounded-lg hover:bg-hover/50"
          >
            {{ t("common.cancel") }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
