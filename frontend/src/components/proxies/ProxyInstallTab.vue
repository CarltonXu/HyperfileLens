<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  ClipboardDocumentIcon,
  DocumentDuplicateIcon,
  ExclamationTriangleIcon,
  KeyIcon,
} from "@heroicons/vue/24/outline";
import type { ProxyNode } from "@/types/proxy";

defineProps<{
  proxy: ProxyNode | null;
}>();

const emit = defineEmits<{
  copy: [text: string, label?: string];
  regenerateToken: [];
}>();

const { t } = useI18n();

function copyIfPresent(text: string | null | undefined, label: string) {
  if (!text) return;
  emit("copy", text, label);
}
</script>

<template>
  <div class="space-y-4">
    <template v-if="proxy">
      <div
        class="p-3 bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 rounded-lg flex items-start gap-3"
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

      <div class="bg-slate-900 rounded-xl p-4">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs text-foreground-muted">
            {{ t("proxies.installInfo.installCommand") }}
          </span>
          <button
            @click="copyIfPresent(proxy.install_command, 'Command')"
            class="text-foreground-muted hover:text-white disabled:opacity-50"
            :disabled="!proxy.install_command"
          >
            <DocumentDuplicateIcon class="w-4 h-4" />
          </button>
        </div>
        <pre class="text-sm text-slate-300 whitespace-pre-wrap break-all">{{
          proxy.install_command || "-"
        }}</pre>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div class="bg-background-secondary rounded-lg p-4">
          <p class="text-xs text-foreground-secondary mb-1">
            {{ t("proxies.install.proxyId") }}
          </p>
          <div class="flex items-center gap-2">
            <code class="text-sm text-foreground font-mono truncate">
              {{ proxy.id }}
            </code>
            <button
              @click="copyIfPresent(proxy.id, 'Proxy ID')"
              class="text-foreground-muted hover:text-indigo-600"
            >
              <ClipboardDocumentIcon class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
        <div class="bg-background-secondary rounded-lg p-4">
          <p class="text-xs text-foreground-secondary mb-1">
            {{ t("proxies.install.apiToken") }}
          </p>
          <div class="flex items-center gap-2">
            <code class="text-sm text-foreground font-mono truncate">
              {{
                proxy.api_token ? `${proxy.api_token.substring(0, 12)}...` : "-"
              }}
            </code>
            <button
              v-if="proxy.api_token"
              @click="copyIfPresent(proxy.api_token, 'API Token')"
              class="text-foreground-muted hover:text-indigo-600"
            >
              <ClipboardDocumentIcon class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <span
          :class="[
            'px-3 py-1 rounded-full text-xs font-medium',
            proxy.install_token_used
              ? 'bg-background-tertiary text-foreground-secondary'
              : 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400',
          ]"
        >
          {{
            proxy.install_token_used
              ? t("proxies.installInfo.tokenUsed")
              : t("proxies.installInfo.tokenAvailable")
          }}
        </span>
      </div>

      <button
        @click="emit('regenerateToken')"
        class="w-full px-4 py-2 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors flex items-center justify-center gap-2"
      >
        <KeyIcon class="w-4 h-4" />
        {{ t("proxies.actions.regenerateToken") }}
      </button>
    </template>
  </div>
</template>
