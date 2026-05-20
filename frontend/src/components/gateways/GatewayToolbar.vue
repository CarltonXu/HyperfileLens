<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  ArrowPathIcon,
  Bars3Icon,
  MagnifyingGlassIcon,
  Squares2X2Icon,
} from "@heroicons/vue/24/outline";

const searchQuery = defineModel<string>("searchQuery", { required: true });
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
  <div class="flex items-center gap-4 mb-6">
    <div class="flex-1 relative">
      <MagnifyingGlassIcon
        class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400"
      />
      <input
        v-model="searchQuery"
        type="text"
        :placeholder="t('gateways.searchPlaceholder')"
        class="w-full pl-10 pr-4 py-2 surface-card border border-border rounded-lg text-foreground placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-violet-500"
      />
    </div>
    <select
      v-model="selectedStatus"
      class="px-4 py-2 surface-card border border-border rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-violet-500"
    >
      <option value="all">{{ t("gateways.allStatus") }}</option>
      <option value="online">{{ t("gateways.statusOnline") }}</option>
      <option value="offline">{{ t("gateways.statusOffline") }}</option>
      <option value="pending">{{ t("gateways.statusPending") }}</option>
      <option value="error">{{ t("gateways.statusError") }}</option>
    </select>
    <button
      @click="$emit('refresh')"
      class="p-2 text-foreground-secondary hover:text-foreground hover:bg-hover rounded-lg"
    >
      <ArrowPathIcon class="w-5 h-5" />
    </button>
    <div class="flex rounded-lg border border-border overflow-hidden">
      <button
        @click="viewMode = 'card'"
        :class="[
          'p-2 transition-colors',
          viewMode === 'card'
            ? 'bg-primary text-primary-foreground'
            : 'surface-card text-foreground-secondary hover:bg-hover',
        ]"
        :title="t('repository.viewModes.card')"
      >
        <Squares2X2Icon class="w-5 h-5" />
      </button>
      <button
        @click="viewMode = 'list'"
        :class="[
          'p-2 transition-colors',
          viewMode === 'list'
            ? 'bg-primary text-primary-foreground'
            : 'surface-card text-foreground-secondary hover:bg-hover',
        ]"
        :title="t('repository.viewModes.list')"
      >
        <Bars3Icon class="w-5 h-5" />
      </button>
    </div>
  </div>
</template>
