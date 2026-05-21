<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  EyeIcon,
  LinkIcon,
  PencilIcon,
  TrashIcon,
} from "@heroicons/vue/24/outline";
import type { ResourceType, SourceResource } from "@/types/sourceResource";

defineProps<{
  resources: SourceResource[];
  getResourceIcon: (type: ResourceType) => any;
  getSourceConnection: (resource: SourceResource) => string;
  getUsagePercent: (resource: SourceResource) => number;
  formatBytes: (bytes?: number | null) => string;
}>();

defineEmits<{
  detail: [resource: SourceResource];
  edit: [resource: SourceResource];
  delete: [resource: SourceResource];
  test: [resource: SourceResource];
}>();

const { t } = useI18n();
</script>

<template>
  <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
    <div
      v-for="resource in resources"
      :key="resource.id"
      class="rounded-xl border border-border bg-card shadow-sm transition-shadow hover:shadow-md"
    >
      <div class="p-4">
        <div class="flex items-start justify-between">
          <div class="flex min-w-0 items-center gap-3">
            <div
              :class="[
                'flex h-10 w-10 shrink-0 items-center justify-center rounded-lg',
                resource.status === 'active'
                  ? 'bg-emerald-100'
                  : resource.status === 'error'
                    ? 'bg-red-100'
                    : 'bg-slate-100',
              ]"
            >
              <component
                :is="getResourceIcon(resource.resource_type)"
                :class="[
                  'h-5 w-5',
                  resource.status === 'active'
                    ? 'text-emerald-600'
                    : resource.status === 'error'
                      ? 'text-red-600'
                      : 'text-slate-400',
                ]"
              />
            </div>
            <div class="min-w-0">
              <h3 class="truncate font-medium text-foreground">
                {{ resource.name }}
              </h3>
              <p class="text-sm text-foreground-secondary dark:text-slate-400">
                {{ resource.resource_type_display || resource.resource_type }}
              </p>
            </div>
          </div>
          <span
            :class="[
              'inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-xs font-medium',
              resource.status === 'active'
                ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                : resource.status === 'error'
                  ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                  : 'bg-background-tertiary text-slate-600',
            ]"
          >
            {{ resource.status_display || resource.status }}
          </span>
        </div>

        <div class="mt-4 rounded-lg bg-background-secondary p-3">
          <div
            class="flex items-center gap-2 text-xs text-foreground-secondary"
          >
            <LinkIcon class="h-4 w-4 text-foreground-muted" />
            <span>{{ t("sourceResources.connection") }}</span>
          </div>
          <p class="mt-1 truncate font-mono text-sm text-foreground">
            {{ getSourceConnection(resource) }}
          </p>
        </div>

        <div class="mt-3 rounded-lg bg-background-secondary p-3">
          <div class="flex items-center justify-between text-xs">
            <span class="text-foreground-secondary">
              {{ t("sourceResources.capacity") }}
            </span>
            <span class="font-medium text-foreground">
              {{
                resource.total_size
                  ? `${getUsagePercent(resource).toFixed(1)}%`
                  : "-"
              }}
            </span>
          </div>
          <div
            class="mt-2 h-2 overflow-hidden rounded-full bg-background-tertiary"
          >
            <div
              class="h-full rounded-full bg-blue-500 transition-all"
              :style="{ width: `${getUsagePercent(resource)}%` }"
            />
          </div>
          <div
            class="mt-2 flex items-center justify-between text-xs text-foreground-secondary"
          >
            <span>{{ formatBytes(resource.used_size) }}</span>
            <span>{{ formatBytes(resource.total_size) }}</span>
          </div>
        </div>

        <div class="mt-4 flex items-center gap-2">
          <LinkIcon class="h-4 w-4 text-slate-400" />
          <span
            v-if="resource.bound_node"
            class="text-sm text-foreground-secondary"
          >
            {{ resource.bound_node.name }}
          </span>
          <span v-else class="text-sm text-slate-400">
            {{ t("sourceResources.noBoundNode") }}
          </span>
        </div>

        <div
          class="mt-4 flex items-center justify-between border-t border-border pt-4"
        >
          <button
            class="rounded-lg px-3 py-1.5 text-sm text-indigo-600 transition-colors hover:bg-indigo-50"
            @click="$emit('test', resource)"
          >
            {{ t("sourceResources.testConnection") }}
          </button>
          <div class="flex gap-1">
            <button
              class="rounded p-1.5 text-foreground-muted hover:bg-hover hover:text-foreground-secondary"
              :title="t('common.view')"
              @click="$emit('detail', resource)"
            >
              <EyeIcon class="h-4 w-4" />
            </button>
            <button
              class="rounded p-1.5 text-foreground-muted hover:bg-hover hover:text-foreground-secondary"
              :title="t('common.edit')"
              @click="$emit('edit', resource)"
            >
              <PencilIcon class="h-4 w-4" />
            </button>
            <button
              class="rounded p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600"
              :title="t('common.delete')"
              @click="$emit('delete', resource)"
            >
              <TrashIcon class="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
