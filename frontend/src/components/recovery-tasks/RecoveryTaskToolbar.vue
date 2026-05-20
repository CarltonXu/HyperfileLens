<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  ArrowPathIcon,
  MagnifyingGlassIcon,
} from "@heroicons/vue/24/outline";

const searchQuery = defineModel<string>("searchQuery", { required: true });
const selectedStatus = defineModel<string>("selectedStatus", { required: true });

defineEmits<{
  refresh: [];
}>();

const { t } = useI18n();
</script>

<template>
  <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
    <div class="flex flex-wrap items-center gap-3">
      <div class="relative flex-1 min-w-[200px]">
        <MagnifyingGlassIcon
          class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400"
        />
        <input
          v-model="searchQuery"
          type="text"
          :placeholder="t('common.search')"
          class="w-full pl-9 pr-4 py-2 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500"
        />
      </div>
      <select
        v-model="selectedStatus"
        class="px-3 py-2 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500"
      >
        <option class="bg-background" value="all">
          {{ t("common.status") }}: {{ t("common.all") }}
        </option>
        <option class="bg-background" value="pending">
          {{ t("recoveryTasks.status.pending") }}
        </option>
        <option class="bg-background" value="running">
          {{ t("recoveryTasks.status.running") }}
        </option>
        <option class="bg-background" value="completed">
          {{ t("recoveryTasks.status.completed") }}
        </option>
        <option class="bg-background" value="failed">
          {{ t("recoveryTasks.status.failed") }}
        </option>
      </select>
      <button
        @click="$emit('refresh')"
        class="inline-flex items-center gap-2 px-3 py-2 text-sm text-foreground-secondary border border-border rounded-lg hover:bg-hover"
      >
        <ArrowPathIcon class="w-4 h-4" />
        {{ t("common.refresh") }}
      </button>
    </div>
  </div>
</template>
