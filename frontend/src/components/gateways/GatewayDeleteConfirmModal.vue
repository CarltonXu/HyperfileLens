<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { ExclamationTriangleIcon } from "@heroicons/vue/24/outline";

interface Gateway {
  id: string;
  name: string;
}

defineProps<{
  gateway: Gateway | null;
}>();

defineEmits<{
  close: [];
  confirm: [];
}>();

const { t } = useI18n();
</script>

<template>
  <div
    class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
  >
    <div class="modal-surface rounded-2xl shadow-xl max-w-md w-full p-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold text-foreground">
          {{ t("gateways.delete.title") }}
        </h2>
        <button
          @click="$emit('close')"
          class="p-1.5 text-foreground-muted hover:text-foreground-secondary hover:bg-hover rounded-lg"
        >
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div class="flex items-start gap-4 mb-6">
        <div
          class="w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center flex-shrink-0"
        >
          <ExclamationTriangleIcon class="w-5 h-5 text-red-600 dark:text-red-400" />
        </div>
        <div>
          <p class="text-foreground">
            {{ t("gateways.delete.message") }}
          </p>
          <p class="text-sm font-medium text-foreground mt-1">
            {{ gateway?.name }}
          </p>
          <p class="text-sm text-foreground-secondary mt-2">
            {{ t("gateways.delete.warning") }}
          </p>
        </div>
      </div>

      <div class="flex justify-end gap-3">
        <button
          @click="$emit('close')"
          class="px-4 py-2 text-sm font-medium text-foreground-secondary bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
        >
          {{ t("common.cancel") }}
        </button>
        <button
          @click="$emit('confirm')"
          class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
        >
          {{ t("gateways.delete.confirm") }}
        </button>
      </div>
    </div>
  </div>
</template>
