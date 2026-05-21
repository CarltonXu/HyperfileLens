<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { XMarkIcon } from "@heroicons/vue/24/outline";
import type { ResourceType, SourceResource } from "@/types/sourceResource";

defineProps<{
  resource: SourceResource;
  configRows: Array<{ label: string; value: string }>;
  statsRows: Array<{ label: string; value: string }>;
  getResourceIcon: (type: ResourceType) => any;
  getUsagePercent: (resource: SourceResource) => number;
  getCapacityText: (resource: SourceResource) => string;
}>();

defineEmits<{
  close: [];
}>();

const { t } = useI18n();
</script>

<template>
  <div class="fixed inset-0 z-50 overflow-y-auto">
    <div class="flex min-h-full items-center justify-center p-4">
      <div class="fixed inset-0 bg-black/50" @click="$emit('close')" />
      <div
        class="relative max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl modal-surface shadow-xl"
      >
        <div
          class="sticky top-0 z-10 flex items-center justify-between border-b border-border px-6 py-4 modal-surface"
        >
          <div class="min-w-0">
            <h2 class="truncate text-lg font-semibold text-foreground">
              {{ resource.name }}
            </h2>
            <p class="mt-1 truncate text-sm text-foreground-secondary">
              {{
                resource.description ||
                resource.resource_type_display ||
                resource.resource_type
              }}
            </p>
          </div>
          <button class="rounded-lg p-1 hover:bg-hover" @click="$emit('close')">
            <XMarkIcon class="h-5 w-5 text-foreground-muted" />
          </button>
        </div>

        <div class="space-y-4 p-6">
          <div class="flex items-center gap-3">
            <div
              :class="[
                'flex h-12 w-12 items-center justify-center rounded-lg',
                resource.resource_type === 's3'
                  ? 'bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400'
                  : resource.resource_type === 'local'
                    ? 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400'
                    : 'bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400',
              ]"
            >
              <component
                :is="getResourceIcon(resource.resource_type)"
                class="h-6 w-6"
              />
            </div>
            <div class="min-w-0 flex-1">
              <p class="font-medium text-foreground">
                {{ resource.resource_type_display || resource.resource_type }}
              </p>
              <p class="text-sm text-foreground-secondary">
                {{ resource.status_display || resource.status }}
              </p>
            </div>
            <span
              :class="
                resource.status === 'active'
                  ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                  : resource.status === 'error'
                    ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                    : 'bg-background-secondary text-foreground-secondary'
              "
              class="inline-flex items-center rounded-full px-3 py-1 text-xs font-medium"
            >
              {{ resource.status_display || resource.status || "-" }}
            </span>
          </div>

          <div class="grid grid-cols-1 gap-3 md:grid-cols-3">
            <div class="rounded-lg bg-background-secondary p-4">
              <p class="text-xs text-foreground-secondary">
                {{ t("sourceResources.form.type") }}
              </p>
              <p class="mt-1 font-semibold text-foreground">
                {{ resource.resource_type_display || resource.resource_type }}
              </p>
            </div>
            <div class="rounded-lg bg-background-secondary p-4">
              <p class="text-xs text-foreground-secondary">
                {{ t("sourceResources.status.label") }}
              </p>
              <p
                :class="[
                  'mt-1 font-semibold',
                  resource.status === 'active'
                    ? 'text-emerald-600 dark:text-emerald-400'
                    : resource.status === 'error'
                      ? 'text-red-600 dark:text-red-400'
                      : 'text-foreground',
                ]"
              >
                {{ resource.status_display || resource.status }}
              </p>
            </div>
            <div class="rounded-lg bg-background-secondary p-4">
              <p class="text-xs text-foreground-secondary">
                {{ t("sourceResources.capacity") }}
              </p>
              <p class="mt-1 font-semibold text-foreground">
                {{ getCapacityText(resource) }}
              </p>
              <div
                class="mt-3 h-2 overflow-hidden rounded-full bg-background-tertiary"
              >
                <div
                  class="h-full rounded-full bg-blue-500"
                  :style="{ width: `${getUsagePercent(resource)}%` }"
                />
              </div>
            </div>
          </div>

          <div class="rounded-lg bg-background-secondary p-4">
            <h3 class="mb-3 text-sm font-semibold text-foreground">
              {{ t("sourceResources.details.connectionConfig") }}
            </h3>
            <dl class="grid grid-cols-1 gap-3 md:grid-cols-2">
              <div
                v-for="row in configRows"
                :key="row.label"
                class="rounded-lg bg-background/60 px-3 py-2"
              >
                <dt class="text-xs text-foreground-secondary">
                  {{ row.label }}
                </dt>
                <dd class="mt-1 break-all text-sm font-medium text-foreground">
                  {{ row.value || "-" }}
                </dd>
              </div>
              <div
                v-if="configRows.length === 0"
                class="text-sm text-foreground-secondary md:col-span-2"
              >
                {{ t("common.noData") }}
              </div>
            </dl>
          </div>

          <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div class="rounded-lg bg-background-secondary p-4">
              <h3 class="mb-3 text-sm font-semibold text-foreground">
                {{ t("sourceResources.details.boundNode") }}
              </h3>
              <dl class="space-y-3">
                <div>
                  <dt class="text-xs text-foreground-secondary">
                    {{ t("common.name") }}
                  </dt>
                  <dd class="mt-1 text-sm font-medium text-foreground">
                    {{ resource.bound_node?.name || "-" }}
                  </dd>
                </div>
                <div>
                  <dt class="text-xs text-foreground-secondary">
                    {{ t("common.status") }}
                  </dt>
                  <dd class="mt-1 text-sm font-medium text-foreground">
                    {{ resource.bound_node?.status || "-" }}
                  </dd>
                </div>
              </dl>
            </div>

            <div class="rounded-lg bg-background-secondary p-4">
              <h3 class="mb-3 text-sm font-semibold text-foreground">
                {{ t("sourceResources.details.statistics") }}
              </h3>
              <dl class="space-y-3">
                <div v-for="row in statsRows" :key="row.label">
                  <dt class="text-xs text-foreground-secondary">
                    {{ row.label }}
                  </dt>
                  <dd class="mt-1 text-sm font-medium text-foreground">
                    {{ row.value }}
                  </dd>
                </div>
              </dl>
            </div>
          </div>

          <div class="rounded-lg bg-background-secondary p-4">
            <h3 class="mb-3 text-sm font-semibold text-foreground">
              {{ t("sourceResources.details.runtime") }}
            </h3>
            <dl class="grid grid-cols-1 gap-3 md:grid-cols-2">
              <div class="rounded-lg bg-background/60 px-3 py-2">
                <dt class="text-xs text-foreground-secondary">
                  {{ t("sourceResources.details.statusMessage") }}
                </dt>
                <dd class="mt-1 break-all text-sm font-medium text-foreground">
                  {{ resource.status_message || "-" }}
                </dd>
              </div>
              <div class="rounded-lg bg-background/60 px-3 py-2">
                <dt class="text-xs text-foreground-secondary">
                  {{ t("sourceResources.details.mountError") }}
                </dt>
                <dd class="mt-1 break-all text-sm font-medium text-foreground">
                  {{ resource.mount_error || "-" }}
                </dd>
              </div>
            </dl>
          </div>
        </div>

        <div
          class="sticky bottom-0 flex justify-end border-t border-border px-6 py-4 modal-surface"
        >
          <button
            class="rounded-lg px-4 py-2 text-sm text-foreground-secondary hover:bg-hover"
            @click="$emit('close')"
          >
            {{ t("common.close") }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
