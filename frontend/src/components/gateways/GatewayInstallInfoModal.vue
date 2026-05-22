<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  DocumentDuplicateIcon,
  ExclamationTriangleIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline";

interface Gateway {
  id: string;
  name: string;
}

defineProps<{
  gateway: Gateway;
  installCommand: string;
  loading: boolean;
  commandCopied: boolean;
}>();

defineEmits<{
  close: [];
  copy: [];
}>();

const { t } = useI18n();
</script>

<template>
  <div
    class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 overflow-y-auto"
  >
    <div class="modal-surface rounded-2xl shadow-xl max-w-2xl w-full my-8">
      <div class="flex items-center justify-between p-5 border-b border-border">
        <div>
          <h2 class="text-lg font-semibold text-foreground">
            {{ t("gateways.installInfo.title") }}
          </h2>
          <p class="text-sm text-foreground-secondary mt-1">
            {{ gateway.name }}
          </p>
        </div>
        <button
          class="p-1.5 text-foreground-muted hover:text-foreground-secondary hover:bg-hover rounded-lg"
          @click="$emit('close')"
        >
          <XMarkIcon class="w-5 h-5" />
        </button>
      </div>

      <div
        class="mx-5 mt-4 p-3 bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 rounded-lg flex items-start gap-3"
      >
        <ExclamationTriangleIcon
          class="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5"
        />
        <div>
          <p class="text-sm font-medium text-amber-800 dark:text-amber-200">
            {{ t("gateways.installInfo.warning") }}
          </p>
          <p class="text-xs text-amber-600 dark:text-amber-400 mt-1">
            {{ t("gateways.installInfo.warningDesc") }}
          </p>
        </div>
      </div>

      <div class="p-5 space-y-5">
        <div class="space-y-2">
          <div class="flex items-center gap-2">
            <span
              class="flex items-center justify-center w-6 h-6 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 text-sm font-medium"
            >
              1
            </span>
            <h3 class="font-medium text-foreground">
              {{ t("gateways.installInfo.installCommand") }}
            </h3>
          </div>

          <div class="relative bg-slate-900 rounded-lg p-4 min-h-[96px]">
            <div v-if="loading" class="flex items-center justify-center py-6">
              <div
                class="w-6 h-6 border-2 border-slate-600 border-t-slate-200 rounded-full animate-spin"
              />
            </div>
            <code
              v-else
              class="text-sm text-slate-300 break-all whitespace-pre-wrap"
            >
              {{ installCommand || t("gateways.installInfo.noCommand") }}
            </code>
            <div class="absolute top-2 right-2 flex gap-2">
              <button
                :disabled="!installCommand || loading"
                class="p-1.5 bg-slate-700 hover:bg-slate-600 rounded text-slate-300 hover:text-white transition-colors disabled:opacity-50"
                :title="t('common.copy')"
                @click="$emit('copy')"
              >
                <DocumentDuplicateIcon class="w-4 h-4" />
              </button>
            </div>
          </div>
          <p v-if="commandCopied" class="text-xs text-emerald-600">
            {{ t("common.copied") }}
          </p>
        </div>

        <div class="bg-blue-50 rounded-lg p-4">
          <h4 class="text-sm font-medium text-blue-800 mb-2">
            {{ t("gateways.installInfo.help") }}
          </h4>
          <ul class="text-xs text-blue-600 space-y-1 list-disc list-inside">
            <li>{{ t("gateways.installInfo.helpStep1") }}</li>
            <li>{{ t("gateways.installInfo.helpStep2") }}</li>
            <li>{{ t("gateways.installInfo.helpStep3") }}</li>
          </ul>
        </div>
      </div>

      <div class="flex items-center justify-end p-5 border-t border-border">
        <button
          class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
          @click="$emit('close')"
        >
          {{ t("common.close") }}
        </button>
      </div>
    </div>
  </div>
</template>
