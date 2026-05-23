<script setup lang="ts">
import { useI18n } from "vue-i18n";
import VChart from "vue-echarts";

defineProps<{
  networkBytesChartOption: any;
  networkPacketsChartOption: any;
}>();

const { t } = useI18n();
</script>

<template>
  <div class="space-y-4">
    <div>
      <h5 class="text-xs text-foreground-secondary mb-2">
        {{ t("gateways.monitoring.networkBytes") }}
      </h5>
      <div class="h-64">
        <VChart :option="networkBytesChartOption" />
      </div>
    </div>

    <div>
      <h5 class="text-xs text-foreground-secondary mb-2">
        {{ t("gateways.monitoring.networkPackets") }}
      </h5>
      <div class="h-64">
        <VChart :option="networkPacketsChartOption" />
      </div>
    </div>
  </div>
</template>
