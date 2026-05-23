<script setup lang="ts">
import { useI18n } from "vue-i18n";

defineProps<{
  stats: {
    rxPackets: number;
    txPackets: number;
    rxDrop: number;
    txErrs: number;
  };
  formatNumber: (value?: number | null) => string;
}>();

const { t } = useI18n();
</script>

<template>
  <div class="grid grid-cols-4 gap-4">
    <div class="bg-blue-50 rounded-lg p-2">
      <p class="text-xs text-foreground-secondary">
        {{ t("gateways.monitoring.rxPackets") }}
      </p>
      <p class="text-sm font-medium text-blue-700 dark:text-blue-300">
        {{ formatNumber(stats.rxPackets) }}
      </p>
    </div>
    <div class="bg-green-50 rounded-lg p-2">
      <p class="text-xs text-foreground-secondary">
        {{ t("gateways.monitoring.txPackets") }}
      </p>
      <p class="text-sm font-medium text-green-700">
        {{ formatNumber(stats.txPackets) }}
      </p>
    </div>
    <div class="bg-red-50 rounded-lg p-2">
      <p class="text-xs text-foreground-secondary">
        {{ t("gateways.monitoring.rxDrop") }}
      </p>
      <p class="text-sm font-medium text-red-700">
        {{ formatNumber(stats.rxDrop) }}
      </p>
    </div>
    <div class="bg-orange-50 rounded-lg p-2">
      <p class="text-xs text-foreground-secondary">
        {{ t("gateways.monitoring.txErrs") }}
      </p>
      <p class="text-sm font-medium text-orange-700">
        {{ formatNumber(stats.txErrs) }}
      </p>
    </div>
  </div>
</template>
