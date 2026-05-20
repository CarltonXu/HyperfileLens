<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  ArrowPathIcon,
  Bars3Icon,
  MagnifyingGlassIcon,
  Squares2X2Icon,
} from "@heroicons/vue/24/outline";

defineProps<{
  searchQuery: string;
  typeFilter: string;
  viewMode: "card" | "list";
}>();

const emit = defineEmits<{
  "update:searchQuery": [value: string];
  "update:typeFilter": [value: string];
  "update:viewMode": [value: "card" | "list"];
  refresh: [];
}>();

const { t } = useI18n();
</script>

<template>
  <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
    <div class="flex flex-wrap items-center gap-3">
      <div class="relative flex-1 min-w-[200px]">
        <MagnifyingGlassIcon
          class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground-muted"
        />
        <input
          :value="searchQuery"
          type="text"
          :placeholder="t('common.search')"
          class="w-full pl-9 pr-4 py-2 text-sm border border-border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
          @input="
            emit(
              'update:searchQuery',
              ($event.target as HTMLInputElement).value,
            )
          "
        />
      </div>
      <select
        :value="typeFilter"
        class="px-3 py-2 text-sm border border-border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
        @change="
          emit('update:typeFilter', ($event.target as HTMLSelectElement).value)
        "
      >
        <option class="bg-background/50" value="">
          {{ t("sourceResources.allTypes") }}
        </option>
        <option class="bg-background/50" value="s3">S3</option>
        <option class="bg-background/50" value="local">
          {{ t("repository.types.local") }}
        </option>
        <option class="bg-background/50" value="nas">NAS/NFS</option>
      </select>
      <button
        @click="emit('refresh')"
        class="inline-flex items-center gap-2 px-3 py-2 text-sm text-foreground-secondary border border-border rounded-lg hover:bg-hover/50 transition-colors"
      >
        <ArrowPathIcon class="w-4 h-4" />
        {{ t("common.refresh") }}
      </button>
      <div class="flex items-center border border-border rounded-md">
        <button
          @click="emit('update:viewMode', 'card')"
          :class="[
            'p-2 rounded-md transition-colors',
            viewMode === 'card'
              ? 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400'
              : 'text-foreground-muted hover:text-foreground-secondary dark:hover:text-slate-300 hover:bg-hover/50',
          ]"
          :title="t('repository.viewModes.card')"
        >
          <Squares2X2Icon class="w-4 h-4" />
        </button>
        <button
          @click="emit('update:viewMode', 'list')"
          :class="[
            'p-2 rounded-md transition-colors',
            viewMode === 'list'
              ? 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400'
              : 'text-foreground-muted hover:text-foreground-secondary dark:hover:text-slate-300 hover:bg-hover/50',
          ]"
          :title="t('repository.viewModes.list')"
        >
          <Bars3Icon class="w-4 h-4" />
        </button>
      </div>
    </div>
  </div>
</template>
