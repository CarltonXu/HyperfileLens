<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { XMarkIcon } from "@heroicons/vue/24/outline";

defineProps<{
  gateway: {
    name: string;
    description: string;
    labels: string;
  };
  creating: boolean;
}>();

const emit = defineEmits<{
  close: [];
  submit: [];
}>();

const { t } = useI18n();
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
    <div class="modal-surface rounded-xl w-full max-w-lg p-6">
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-xl font-semibold text-foreground">
          {{ t("gateways.createGateway") }}
        </h2>
        <button
          class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
          @click="emit('close')"
        >
          <XMarkIcon class="w-6 h-6" />
        </button>
      </div>

      <form class="space-y-4" @submit.prevent="emit('submit')">
        <div>
          <label
            class="block text-sm font-medium text-foreground-secondary mb-1"
          >
            {{ t("gateways.gatewayName") }}
            <span class="text-red-500">*</span>
          </label>
          <input
            v-model="gateway.name"
            type="text"
            required
            class="w-full px-3 py-2 bg-background-secondary border border-border rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-violet-500"
            :placeholder="t('gateways.gatewayNamePlaceholder')"
          />
        </div>

        <div>
          <label
            class="block text-sm font-medium text-foreground-secondary mb-1"
          >
            {{ t("gateways.description") }}
          </label>
          <textarea
            v-model="gateway.description"
            rows="2"
            class="w-full px-3 py-2 bg-background-secondary border border-border rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-violet-500"
            :placeholder="t('gateways.descriptionPlaceholder')"
          />
        </div>

        <div>
          <label
            class="block text-sm font-medium text-foreground-secondary mb-1"
          >
            {{ t("gateways.labels") }}
          </label>
          <input
            v-model="gateway.labels"
            type="text"
            class="w-full px-3 py-2 bg-background-secondary border border-border rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-violet-500"
            :placeholder="t('gateways.labelsPlaceholder')"
          />
          <p class="mt-1 text-xs text-foreground-secondary">
            {{ t("gateways.labelsHint") }}
          </p>
        </div>

        <div class="flex justify-end gap-3 pt-4">
          <button
            type="button"
            class="px-4 py-2 text-foreground-secondary hover:bg-hover rounded-lg"
            @click="emit('close')"
          >
            {{ t("common.cancel") }}
          </button>
          <button
            type="submit"
            :disabled="creating || !gateway.name.trim()"
            class="px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ creating ? t("common.loading") : t("common.create") }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
