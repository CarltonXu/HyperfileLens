<script setup lang="ts">
import { useI18n } from "vue-i18n";

defineProps<{
  stats: {
    total: number;
    active: number;
    totalCapacity: number;
    totalUsed: number;
  };
  formatBytes: (bytes: number) => string;
}>();

const { t } = useI18n();
</script>

<template>
  <div class="grid grid-cols-1 sm:grid-cols-4 gap-4">
    <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
      <p class="text-xs text-foreground-secondary">
        {{ t("repository.stats.total") }}
      </p>
      <p class="text-xl font-bold text-foreground mt-1">{{ stats.total }}</p>
    </div>
    <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
      <p class="text-xs text-foreground-secondary">
        {{ t("repository.stats.active") }}
      </p>
      <p class="text-xl font-bold text-emerald-600 mt-1">
        {{ stats.active }}
      </p>
    </div>
    <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
      <p class="text-xs text-foreground-secondary">
        {{ t("repository.stats.totalCapacity") }}
      </p>
      <p class="text-xl font-bold text-foreground mt-1">
        {{ formatBytes(stats.totalCapacity) }}
      </p>
    </div>
    <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
      <p class="text-xs text-foreground-secondary">
        {{ t("repository.stats.usedSpace") }}
      </p>
      <p class="text-xl font-bold text-blue-600 mt-1">
        {{ formatBytes(stats.totalUsed) }}
      </p>
    </div>
  </div>
</template>
