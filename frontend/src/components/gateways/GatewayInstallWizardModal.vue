<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  ArrowPathIcon,
  CheckCircleIcon,
  ClipboardDocumentIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline";

defineProps<{
  gateway: {
    id: string;
    name: string;
  };
  step: number;
  installCommand: string;
  loadingCommand: boolean;
}>();

const emit = defineEmits<{
  close: [];
  previous: [];
  next: [];
  copyCommand: [];
}>();

const { t } = useI18n();
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
    <div class="modal-surface rounded-xl w-full max-w-2xl p-6">
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-xl font-semibold text-foreground">
          {{ t("gateways.installWizard.title") }}
        </h2>
        <button
          class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
          @click="emit('close')"
        >
          <XMarkIcon class="w-6 h-6" />
        </button>
      </div>

      <div class="flex items-center justify-center mb-8">
        <div class="flex items-center">
          <template v-for="item in [1, 2, 3]" :key="item">
            <div
              :class="[
                'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium',
                step >= item
                  ? 'bg-violet-600 text-white'
                  : 'bg-slate-200 text-slate-500',
              ]"
            >
              {{ item }}
            </div>
            <div
              v-if="item < 3"
              :class="[
                'w-16 h-1',
                step >= item + 1 ? 'bg-violet-600' : 'bg-slate-200',
              ]"
            />
          </template>
        </div>
      </div>

      <div v-if="step === 1" class="space-y-4">
        <h3 class="text-lg font-medium text-foreground">
          {{ t("gateways.installWizard.step1Title") }}
        </h3>
        <p class="text-foreground-secondary">
          {{ t("gateways.installWizard.step1Desc") }}
        </p>

        <div class="bg-background-secondary rounded-lg p-4 space-y-3">
          <div class="flex justify-between">
            <span class="text-foreground-secondary">
              {{ t("gateways.gatewayName") }}
            </span>
            <span class="font-medium text-foreground">{{ gateway.name }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-foreground-secondary">
              {{ t("gateways.gatewayId") }}
            </span>
            <span class="font-mono text-sm text-foreground">
              {{ gateway.id }}
            </span>
          </div>
          <div class="flex justify-between">
            <span class="text-foreground-secondary">
              {{ t("gateways.status") }}
            </span>
            <span
              class="px-2 py-1 text-xs font-medium rounded-full bg-background-tertiary text-foreground-secondary"
            >
              {{ t("gateways.statusPending") }}
            </span>
          </div>
        </div>

        <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
          <p class="text-sm text-blue-700 dark:text-blue-300">
            {{ t("gateways.installWizard.step1Note") }}
          </p>
        </div>
      </div>

      <div v-if="step === 2" class="space-y-4">
        <h3 class="text-lg font-medium text-foreground">
          {{ t("gateways.installWizard.step2Title") }}
        </h3>
        <p class="text-foreground-secondary">
          {{ t("gateways.installWizard.step2Desc") }}
        </p>

        <div
          v-if="loadingCommand"
          class="flex items-center justify-center py-8"
        >
          <ArrowPathIcon class="w-6 h-6 text-slate-400 animate-spin" />
        </div>

        <div v-else class="space-y-4">
          <div class="relative">
            <pre
              class="bg-slate-900 text-slate-100 rounded-lg p-4 text-sm overflow-x-auto whitespace-pre-wrap"
              >{{
                installCommand || t("gateways.installWizard.noCommand")
              }}</pre
            >
            <button
              class="absolute top-2 right-2 p-2 bg-slate-700 hover:bg-slate-600 rounded text-slate-300"
              @click="emit('copyCommand')"
            >
              <ClipboardDocumentIcon class="w-4 h-4" />
            </button>
          </div>

          <div class="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-4">
            <p class="text-sm text-yellow-700 dark:text-yellow-300">
              {{ t("gateways.installWizard.step2Note") }}
            </p>
          </div>
        </div>
      </div>

      <div v-if="step === 3" class="space-y-4">
        <h3 class="text-lg font-medium text-foreground">
          {{ t("gateways.installWizard.step3Title") }}
        </h3>
        <p class="text-foreground-secondary">
          {{ t("gateways.installWizard.step3Desc") }}
        </p>

        <div class="flex flex-col items-center py-8">
          <div
            class="w-16 h-16 rounded-full bg-violet-100 dark:bg-violet-900/30 flex items-center justify-center mb-4"
          >
            <ArrowPathIcon
              class="w-8 h-8 text-violet-600 dark:text-violet-400 animate-spin"
            />
          </div>
          <p class="text-foreground-secondary">
            {{ t("gateways.installWizard.waitingForRegistration") }}
          </p>
        </div>

        <div class="bg-background-secondary rounded-lg p-4">
          <h4 class="text-sm font-medium text-foreground mb-2">
            {{ t("gateways.installWizard.checklist") }}
          </h4>
          <ul class="space-y-2 text-sm text-foreground-secondary">
            <li
              v-for="key in ['checklist1', 'checklist2', 'checklist3']"
              :key="key"
              class="flex items-center gap-2"
            >
              <CheckCircleIcon class="w-4 h-4 text-emerald-500" />
              {{ t(`gateways.installWizard.${key}`) }}
            </li>
          </ul>
        </div>
      </div>

      <div class="flex justify-between pt-6 mt-6 border-t border-border">
        <button
          v-if="step > 1"
          class="px-4 py-2 text-foreground-secondary hover:bg-hover rounded-lg"
          @click="emit('previous')"
        >
          {{ t("common.previous") }}
        </button>
        <div v-else />

        <div class="flex gap-3">
          <button
            class="px-4 py-2 text-foreground-secondary hover:bg-hover rounded-lg"
            @click="emit('close')"
          >
            {{ t("common.close") }}
          </button>
          <button
            v-if="step < 3"
            :disabled="step === 2 && !installCommand"
            class="px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed"
            @click="emit('next')"
          >
            {{ t("common.next") }}
          </button>
          <button
            v-else
            class="px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700"
            @click="emit('close')"
          >
            {{ t("common.finish") }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
