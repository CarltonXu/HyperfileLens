<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  ArrowPathIcon,
  Bars3Icon,
  MagnifyingGlassIcon,
  Squares2X2Icon,
} from "@heroicons/vue/24/outline";
import type { ResourceType } from "@/types/sourceResource";

defineProps<{
  resourceTypes: Array<{ value: ResourceType; label: string }>;
}>();

defineEmits<{
  refresh: [];
}>();

const searchQuery = defineModel<string>("searchQuery", { required: true });
const typeFilter = defineModel<string>("typeFilter", { required: true });
const statusFilter = defineModel<string>("statusFilter", { required: true });
const viewMode = defineModel<"card" | "list">("viewMode", { required: true });

const { t } = useI18n();
</script>

<template>
  <div class="rounded-xl border border-border bg-card p-4 shadow-sm">
    <div class="flex flex-wrap items-center gap-3">
      <div class="relative min-w-[200px] flex-1">
        <MagnifyingGlassIcon
          class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
        />
        <input
          v-model="searchQuery"
          type="text"
          :placeholder="t('common.search')"
          class="w-full rounded-lg border border-border bg-background py-2 pl-9 pr-4 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>
      <select
        v-model="typeFilter"
        class="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-indigo-500"
      >
        <option class="bg-background" value="">
          {{ t("sourceResources.allTypes") }}
        </option>
        <option
          v-for="type in resourceTypes"
          :key="type.value"
          class="bg-background"
          :value="type.value"
        >
          {{ type.label }}
        </option>
      </select>
      <select
        v-model="statusFilter"
        class="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-indigo-500"
      >
        <option class="bg-background" value="">
          {{ t("sourceResources.allStatus") }}
        </option>
        <option class="bg-background" value="active">
          {{ t("sourceResources.status.active") }}
        </option>
        <option class="bg-background" value="inactive">
          {{ t("sourceResources.status.inactive") }}
        </option>
        <option class="bg-background" value="error">
          {{ t("sourceResources.status.error") }}
        </option>
      </select>
      <button
        class="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm text-foreground-secondary transition-colors hover:bg-hover"
        @click="$emit('refresh')"
      >
        <ArrowPathIcon class="h-4 w-4" />
        {{ t("common.refresh") }}
      </button>
      <div class="flex overflow-hidden rounded-lg border border-border">
        <button
          :class="[
            'p-2 transition-colors',
            viewMode === 'card'
              ? 'bg-primary text-primary-foreground'
              : 'bg-background text-foreground-secondary hover:bg-hover',
          ]"
          :title="t('repository.viewModes.card')"
          @click="viewMode = 'card'"
        >
          <Squares2X2Icon class="h-4 w-4" />
        </button>
        <button
          :class="[
            'p-2 transition-colors',
            viewMode === 'list'
              ? 'bg-primary text-primary-foreground'
              : 'bg-background text-foreground-secondary hover:bg-hover',
          ]"
          :title="t('repository.viewModes.list')"
          @click="viewMode = 'list'"
        >
          <Bars3Icon class="h-4 w-4" />
        </button>
      </div>
    </div>
  </div>
</template>
