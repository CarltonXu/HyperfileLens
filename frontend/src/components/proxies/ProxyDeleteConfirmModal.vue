<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { ExclamationTriangleIcon } from "@heroicons/vue/24/outline";
import type { ProxyNode } from "@/types/proxy";

defineProps<{
  proxy: ProxyNode;
}>();

const emit = defineEmits<{
  cancel: [];
  confirm: [];
}>();

const { t } = useI18n();
</script>

<template>
  <div
    class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
  >
    <div class="modal-surface rounded-2xl shadow-xl max-w-md w-full">
      <div class="p-6">
        <div
          class="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4"
        >
          <ExclamationTriangleIcon class="w-6 h-6 text-red-600" />
        </div>
        <h3 class="text-lg font-semibold text-foreground text-center mb-2">
          {{ t("proxies.delete.title") }}
        </h3>
        <p class="text-sm text-foreground-secondary text-center">
          {{ t("proxies.delete.description", { name: proxy.name }) }}
        </p>
      </div>
      <div class="flex justify-center gap-3 p-5 border-t border-border">
        <button
          @click="emit('cancel')"
          class="px-4 py-2 text-sm font-medium text-foreground-secondary bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
        >
          {{ t("common.cancel") }}
        </button>
        <button
          @click="emit('confirm')"
          class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
        >
          {{ t("common.delete") }}
        </button>
      </div>
    </div>
  </div>
</template>
