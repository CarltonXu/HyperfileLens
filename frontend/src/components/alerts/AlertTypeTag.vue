<script setup lang="ts">
import { useI18n } from "vue-i18n";

defineProps<{ type: string }>();
const { t } = useI18n();
</script>

<template>
  <span
    class="inline-flex items-center rounded-md border border-border bg-background-secondary px-2 py-1 text-xs font-medium text-foreground">
    {{ t(`alertsCenter.values.${type}`) }}
  </span>
</template>
