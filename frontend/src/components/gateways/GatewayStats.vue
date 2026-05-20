<script setup lang="ts">
import { useI18n } from "vue-i18n";

defineProps<{
  stats: {
    total: number;
    active: number;
    offline: number;
    pending: number;
    error: number;
    total_mounts: number;
  } | null;
}>();

const { t } = useI18n();
</script>

<template>
  <div
    v-if="stats"
    class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6"
  >
    <div class="bg-card rounded-xl border border-border p-4">
      <p class="text-sm text-foreground-secondary">
        {{ t("gateways.statsTotal") }}
      </p>
      <p class="text-2xl font-bold text-foreground mt-1">{{ stats.total }}</p>
    </div>
    <div class="bg-card rounded-xl border border-border p-4">
      <p class="text-sm text-foreground-secondary">
        {{ t("gateways.statsActive") }}
      </p>
      <p class="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">
        {{ stats.active }}
      </p>
    </div>
    <div class="bg-card rounded-xl border border-border p-4">
      <p class="text-sm text-foreground-secondary">
        {{ t("gateways.statsOffline") }}
      </p>
      <p class="text-2xl font-bold text-red-600 dark:text-red-400 mt-1">
        {{ stats.offline }}
      </p>
    </div>
    <div class="bg-card rounded-xl border border-border p-4">
      <p class="text-sm text-foreground-secondary">
        {{ t("gateways.statsPending") }}
      </p>
      <p class="text-2xl font-bold text-foreground-secondary mt-1">
        {{ stats.pending }}
      </p>
    </div>
    <div class="bg-card rounded-xl border border-border p-4">
      <p class="text-sm text-foreground-secondary">
        {{ t("gateways.statsError") }}
      </p>
      <p class="text-2xl font-bold text-red-600 dark:text-red-400 mt-1">
        {{ stats.error }}
      </p>
    </div>
    <div class="bg-card rounded-xl border border-border p-4">
      <p class="text-sm text-foreground-secondary">
        {{ t("gateways.statsMounts") }}
      </p>
      <p class="text-2xl font-bold text-blue-600 dark:text-blue-400 mt-1">
        {{ stats.total_mounts }}
      </p>
    </div>
  </div>
</template>
