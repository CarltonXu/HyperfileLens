<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  ArrowPathIcon,
  DocumentDuplicateIcon,
  ExclamationTriangleIcon,
  KeyIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline";
import type { ProxyNode } from "@/types/proxy";

defineProps<{
  proxy: ProxyNode;
}>();

defineEmits<{
  close: [];
  copy: [text: string, label: string];
  regenerateToken: [];
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
            {{ t("proxies.installInfo.title") }}
          </h2>
          <p class="text-sm text-foreground-secondary mt-1">
            {{ proxy.name }} - {{ t(`proxies.roles.${proxy.role}`) }}
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
            {{ t("proxies.installInfo.warning") }}
          </p>
          <p class="text-xs text-amber-600 dark:text-amber-400 mt-1">
            {{ t("proxies.installInfo.warningDesc") }}
          </p>
        </div>
      </div>

      <div class="p-5 space-y-5">
        <div class="space-y-2">
          <div class="flex items-center gap-2">
            <span
              class="flex items-center justify-center w-6 h-6 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 text-sm font-medium"
              >1</span
            >
            <h3 class="font-medium text-foreground">
              {{ t("proxies.installInfo.installCommand") }}
            </h3>
          </div>
          <div class="relative bg-slate-900 rounded-lg p-4">
            <code
              class="text-sm text-slate-300 break-all whitespace-pre-wrap"
              >{{
                proxy.install_command || t("proxies.installInfo.noCommand")
              }}</code
            >
            <div class="absolute top-2 right-2 flex gap-2">
              <button
                :disabled="!proxy.install_command"
                class="p-1.5 bg-slate-700 hover:bg-slate-600 rounded text-slate-300 hover:text-white transition-colors disabled:opacity-50"
                :title="t('common.copy')"
                @click="
                  proxy.install_command &&
                  $emit('copy', proxy.install_command, 'Command')
                "
              >
                <DocumentDuplicateIcon class="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        <div class="space-y-2">
          <div class="flex items-center gap-2">
            <span
              class="flex items-center justify-center w-6 h-6 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 text-sm font-medium"
              >2</span
            >
            <h3 class="font-medium text-foreground">
              {{ t("proxies.installInfo.credentials") }}
            </h3>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="bg-background-secondary rounded-lg p-4">
              <div class="flex items-center justify-between mb-2">
                <span
                  class="text-xs font-medium text-foreground-secondary uppercase"
                  >{{ t("proxies.installInfo.proxyId") }}</span
                >
              </div>
              <div class="flex items-center justify-between">
                <code class="text-sm text-foreground break-all">{{
                  proxy.id
                }}</code>
                <button
                  class="ml-2 p-1 hover:bg-slate-200 rounded text-foreground-muted hover:text-foreground-secondary"
                  @click="$emit('copy', proxy.id, 'Proxy ID')"
                >
                  <DocumentDuplicateIcon class="w-4 h-4" />
                </button>
              </div>
              <p class="text-xs text-foreground-muted mt-2">
                {{ t("proxies.installInfo.proxyIdDesc") }}
              </p>
            </div>

            <div class="bg-background-secondary rounded-lg p-4">
              <div class="flex items-center justify-between mb-2">
                <span
                  class="text-xs font-medium text-foreground-secondary uppercase"
                  >{{ t("proxies.installInfo.apiToken") }}</span
                >
              </div>
              <div class="flex items-center justify-between">
                <code class="text-sm text-foreground break-all">{{
                  proxy.api_token || "N/A"
                }}</code>
                <button
                  v-if="proxy.api_token"
                  class="ml-2 p-1 hover:bg-slate-200 rounded text-foreground-muted hover:text-foreground-secondary"
                  @click="$emit('copy', proxy.api_token, 'API Token')"
                >
                  <DocumentDuplicateIcon class="w-4 h-4" />
                </button>
              </div>
              <p class="text-xs text-foreground-muted mt-2">
                {{ t("proxies.installInfo.apiTokenDesc") }}
              </p>
            </div>
          </div>

          <div class="bg-background-secondary rounded-lg p-4">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <KeyIcon class="w-4 h-4 text-foreground-muted" />
                <span class="text-sm font-medium text-foreground">{{
                  t("proxies.installInfo.installToken")
                }}</span>
              </div>
              <span
                :class="[
                  'text-xs font-medium px-2 py-1 rounded',
                  proxy.install_token_used
                    ? 'bg-slate-200 text-foreground-secondary'
                    : 'bg-emerald-100 text-emerald-700',
                ]"
              >
                {{
                  proxy.install_token_used
                    ? t("proxies.installInfo.tokenUsed")
                    : t("proxies.installInfo.tokenAvailable")
                }}
              </span>
            </div>
          </div>
        </div>

        <div class="bg-blue-50 rounded-lg p-4">
          <h4 class="text-sm font-medium text-blue-800 mb-2">
            {{ t("proxies.installInfo.help") }}
          </h4>
          <ul class="text-xs text-blue-600 space-y-1 list-disc list-inside">
            <li>{{ t("proxies.installInfo.helpStep1") }}</li>
            <li>{{ t("proxies.installInfo.helpStep2") }}</li>
            <li>{{ t("proxies.installInfo.helpStep3") }}</li>
          </ul>
        </div>
      </div>

      <div class="flex items-center justify-between p-5 border-t border-border">
        <button
          class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 rounded-lg hover:bg-amber-100 transition-colors"
          @click="$emit('regenerateToken')"
        >
          <ArrowPathIcon class="w-4 h-4" />
          {{ t("proxies.actions.regenerateToken") }}
        </button>
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
