<script setup lang="ts">
import { useI18n } from "vue-i18n";

defineProps<{ severity: string }>();
const { t } = useI18n();
</script>

<template>
  <span
    class="inline-flex items-center rounded-md px-2 py-1 text-xs font-medium"
    :class="{
      'bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300':
        severity === 'critical',
      'bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300':
        severity === 'warning',
      'bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300':
        severity === 'info',
    }">
    {{ t(`alertsCenter.values.${severity}`) }}
  </span>
</template>
