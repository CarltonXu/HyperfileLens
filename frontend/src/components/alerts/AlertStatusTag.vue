<script setup lang="ts">
import { useI18n } from "vue-i18n";

defineProps<{ status: string }>();
const { t } = useI18n();
</script>

<template>
  <span
    class="inline-flex items-center rounded-md px-2 py-1 text-xs font-medium"
    :class="{
      'bg-zinc-100 text-zinc-700 dark:bg-zinc-500/15 dark:text-zinc-300':
        status === 'pending',
      'bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300':
        status === 'firing',
      'bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300':
        status === 'acknowledged',
      'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300':
        status === 'resolved',
    }">
    {{ t(`alertsCenter.values.${status}`) }}
  </span>
</template>
