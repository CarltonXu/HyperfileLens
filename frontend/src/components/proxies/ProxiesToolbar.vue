<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  ArrowPathIcon,
  Bars3Icon,
  MagnifyingGlassIcon,
  Squares2X2Icon,
} from "@heroicons/vue/24/outline";

const searchQuery = defineModel<string>("searchQuery", { required: true });
const selectedRole = defineModel<string>("selectedRole", { required: true });
const selectedStatus = defineModel<string>("selectedStatus", {
  required: true,
});
const viewMode = defineModel<"card" | "list">("viewMode", { required: true });

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
          class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground-muted"
        />
        <input
          v-model="searchQuery"
          type="text"
          :placeholder="t('common.search')"
          class="w-full pl-9 pr-4 py-2 text-sm border border-border rounded-lg bg-background text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
        />
      </div>
      <select
        v-model="selectedRole"
        class="px-3 py-2 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-indigo-500"
      >
        <option value="all" class="bg-background">
          {{ t("common.role") }}: {{ t("common.all") }}
        </option>
        <option value="agent" class="bg-background">
          {{ t("proxies.roles.agent") }}
        </option>
        <option value="sync" class="bg-background">
          {{ t("proxies.roles.sync") }}
        </option>
      </select>
      <select
        v-model="selectedStatus"
        class="px-3 py-2 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-indigo-500"
      >
        <option value="all" class="bg-background">
          {{ t("common.status") }}: {{ t("common.all") }}
        </option>
        <option value="online" class="bg-background">
          {{ t("proxies.status.online") }}
        </option>
        <option value="pending" class="bg-background">
          {{ t("proxies.status.pending") }}
        </option>
        <option value="offline" class="bg-background">
          {{ t("proxies.status.offline") }}
        </option>
        <option value="error" class="bg-background">
          {{ t("proxies.status.error") }}
        </option>
        <option value="maintenance" class="bg-background">
          {{ t("proxies.status.maintenance") }}
        </option>
      </select>
      <button
        class="inline-flex items-center gap-2 px-3 py-2 text-sm text-foreground-secondary border border-border rounded-lg hover:bg-hover transition-colors"
        @click="$emit('refresh')"
      >
        <ArrowPathIcon class="w-4 h-4" />
        {{ t("common.refresh") }}
      </button>
      <div class="flex items-center gap-1 border border-border rounded-lg p-1">
        <button
          :class="[
            'p-2 rounded-md transition-colors',
            viewMode === 'card'
              ? 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400'
              : 'text-foreground-muted hover:text-foreground-secondary hover:bg-hover',
          ]"
          :title="t('proxies.viewModes.card')"
          @click="viewMode = 'card'"
        >
          <Squares2X2Icon class="w-4 h-4" />
        </button>
        <button
          :class="[
            'p-2 rounded-md transition-colors',
            viewMode === 'list'
              ? 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400'
              : 'text-foreground-muted hover:text-foreground-secondary hover:bg-hover',
          ]"
          :title="t('proxies.viewModes.list')"
          @click="viewMode = 'list'"
        >
          <Bars3Icon class="w-4 h-4" />
        </button>
      </div>
    </div>
  </div>
</template>
