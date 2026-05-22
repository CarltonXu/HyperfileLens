<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  ArrowPathIcon,
  ClipboardDocumentIcon,
  ArrowDownTrayIcon,
  CheckCircleIcon,
} from "@heroicons/vue/24/outline";

interface Gateway {
  id: string;
  name: string;
  status: string;
}

defineProps<{
  gateway: Gateway;
  installCommand: string;
  isLoading: boolean;
}>();

defineEmits<{
  loadCommand: [];
  copyCommand: [];
  downloadConfig: [];
}>();

const { t } = useI18n();
</script>

<template>
  <div class="space-y-6">
    <!-- Pending Status Info -->
    <div
      v-if="gateway.status === 'pending'"
      class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4"
    >
      <p class="text-sm text-blue-700 dark:text-blue-300">
        {{ t("gateways.install.pendingNote") }}
      </p>
    </div>

    <!-- Install Command -->
    <div>
      <h3 class="text-sm font-semibold text-foreground mb-3">
        {{ t("gateways.install.installCommand") }}
      </h3>

      <div
        v-if="isLoading"
        class="flex items-center justify-center py-8"
      >
        <ArrowPathIcon class="w-6 h-6 text-slate-400 animate-spin" />
      </div>

      <div v-else-if="installCommand" class="space-y-4">
        <div class="relative">
          <pre
            class="bg-slate-900 text-slate-100 rounded-lg p-4 text-sm overflow-x-auto whitespace-pre-wrap font-mono"
          >{{ installCommand }}</pre>
          <div class="absolute top-2 right-2 flex gap-2">
            <button
              @click="$emit('downloadConfig')"
              class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-300 bg-slate-700 rounded-lg hover:bg-slate-600"
            >
              <ArrowDownTrayIcon class="w-3.5 h-3.5" />
              {{ t("gateways.install.downloadConfig") }}
            </button>
            <button
              @click="$emit('copyCommand')"
              class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-violet-600 rounded-lg hover:bg-violet-500"
            >
              <ClipboardDocumentIcon class="w-3.5 h-3.5" />
              {{ t("common.copy") }}
            </button>
          </div>
        </div>

        <div
          class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4"
        >
          <p class="text-sm text-amber-700 dark:text-amber-300">
            {{ t("gateways.install.securityNote") }}
          </p>
        </div>
      </div>

      <div
        v-else
        class="flex flex-col items-center justify-center py-8 text-center"
      >
        <p class="text-foreground-secondary mb-4">
          {{ t("gateways.install.noCommand") }}
        </p>
        <button
          @click="$emit('loadCommand')"
          class="px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700"
        >
          {{ t("gateways.install.loadCommand") }}
        </button>
      </div>
    </div>

    <!-- Installation Checklist -->
    <div>
      <h3 class="text-sm font-semibold text-foreground mb-3">
        {{ t("gateways.install.checklist") }}
      </h3>
      <div class="bg-background-secondary rounded-lg p-4">
        <ul class="space-y-3 text-sm">
          <li class="flex items-center gap-3">
            <div
              class="w-6 h-6 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center"
            >
              <CheckCircleIcon class="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            </div>
            <span class="text-foreground-secondary">
              {{ t("gateways.install.checklistUbuntu2204") }}
            </span>
          </li>
          <li class="flex items-center gap-3">
            <div
              class="w-6 h-6 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center"
            >
              <CheckCircleIcon class="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            </div>
            <span class="text-foreground-secondary">
              {{ t("gateways.install.checklistSudoAccess") }}
            </span>
          </li>
          <li class="flex items-center gap-3">
            <div
              class="w-6 h-6 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center"
            >
              <CheckCircleIcon class="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            </div>
            <span class="text-foreground-secondary">
              {{ t("gateways.install.checklistNetworkAccess") }}
            </span>
          </li>
          <li class="flex items-center gap-3">
            <div
              class="w-6 h-6 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center"
            >
              <CheckCircleIcon class="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            </div>
            <span class="text-foreground-secondary">
              {{ t("gateways.install.checklistSshAccess") }}
            </span>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>
