<script setup lang="ts">
import { ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { XMarkIcon } from "@heroicons/vue/24/outline";
import ResourceFlowTopology from "@/components/ResourceFlowTopology.vue";
import { sourceResourcesApi } from "@/api";
import type { BackupTask } from "@/types/backup";
import type { ProxyNode } from "@/types/proxy";
import type { Repository } from "@/types/repository";
import type { SourceResource } from "@/types/sourceResource";

const props = defineProps<{
  resource: SourceResource;
  tasks?: BackupTask[];
  repositories?: Repository[];
  proxies?: ProxyNode[];
  gateways?: any[];
}>();

defineEmits<{
  close: [];
}>();

const { t } = useI18n();
const topology = ref<Record<string, any> | null>(null);
const loading = ref(false);

function fallbackTask() {
  if (topology.value?.task) return topology.value.task as BackupTask;
  return (
    props.tasks?.find((task) => task.source_resource === props.resource.id) ||
    null
  );
}

function fallbackRepository() {
  if (topology.value?.repository)
    return topology.value.repository as Repository;
  const task = fallbackTask();
  if (!task?.target_repository) return null;
  return (
    props.repositories?.find((repo) => repo.id === task.target_repository) ||
    null
  );
}

async function loadTopology() {
  loading.value = true;
  try {
    const response = await sourceResourcesApi.topology(props.resource.id);
    topology.value = response.data;
  } catch (error) {
    console.error("Failed to fetch source topology:", error);
    topology.value = null;
  } finally {
    loading.value = false;
  }
}

watch(
  () => props.resource.id,
  () => {
    loadTopology();
  },
  { immediate: true },
);
</script>

<template>
  <div class="fixed inset-0 z-50 overflow-y-auto">
    <div class="flex min-h-full items-center justify-center p-4">
      <div class="fixed inset-0 bg-black/55" @click="$emit('close')" />
      <div
        class="relative w-full max-w-[1180px] overflow-hidden rounded-2xl border border-border bg-card shadow-2xl"
      >
        <div
          class="flex items-start justify-between gap-4 border-b border-border px-6 py-4"
        >
          <div class="min-w-0">
            <h2 class="truncate text-lg font-semibold text-foreground">
              {{ t("resourceTopology.modal.title") }}
            </h2>
            <p class="mt-1 truncate text-sm text-foreground-secondary">
              {{ resource.name }} ·
              {{ resource.resource_type_display || resource.resource_type }}
            </p>
          </div>
          <button class="rounded-lg p-1 hover:bg-hover" @click="$emit('close')">
            <XMarkIcon class="h-5 w-5 text-foreground-muted" />
          </button>
        </div>

        <div class="max-h-[78vh] overflow-auto p-6">
          <ResourceFlowTopology
            :source="resource"
            :task="fallbackTask()"
            :repository="fallbackRepository()"
            :proxies="proxies || []"
            :gateways="gateways || []"
            :topology="topology"
          />

          <div
            class="mt-4 rounded-lg border border-border bg-background-secondary px-4 py-3 text-sm text-foreground-secondary"
          >
            <span v-if="loading">
              {{ t("resourceTopology.modal.resolving") }}
            </span>
            <span v-else-if="topology?.selection_reason">
              {{ t("resourceTopology.modal.executorSelection") }}:
              {{ topology.selection_reason }}
            </span>
            <span v-else>
              {{ t("resourceTopology.modal.fallback") }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
