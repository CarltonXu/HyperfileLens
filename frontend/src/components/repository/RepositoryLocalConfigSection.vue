<script setup lang="ts">
import { useI18n } from "vue-i18n";
import type { ProxyNode } from "@/types/proxy";
import {
  CheckCircleIcon,
  ChevronRightIcon,
  ExclamationCircleIcon,
  FolderIcon,
  XCircleIcon,
} from "@heroicons/vue/24/outline";

type LocalPathCheckResult = {
  success: boolean;
  path?: string;
  message?: string;
  error?: string;
  exists?: boolean;
  writable?: boolean;
  write_test?: Record<string, any>;
  space_info?: Record<string, any>;
} | null;

defineProps<{
  newRepo: {
    bound_node: string | null;
    local_config: {
      path: string;
    };
  };
  formErrors: Record<string, string>;
  availableSyncProxies: ProxyNode[];
  proxyDirectories: string[];
  currentPath: string;
  isLoadingDirectories: boolean;
  checkingLocalPath: boolean;
  localPathCheckResult: LocalPathCheckResult;
  formatBytes: (bytes: number) => string;
}>();

defineEmits<{
  handleProxySelect: [proxyId: string];
  checkLocalPath: [];
  clearError: [field: string];
  clearLocalPathCheck: [];
  navigateUp: [];
  navigateToDirectory: [directory: string];
  selectCurrentPath: [];
}>();

const { t } = useI18n();
</script>

<template>
  <div class="space-y-4 p-4 rounded-xl border border-border">
    <div
      class="flex items-start gap-2 text-sm text-blue-700 dark:text-blue-400 bg-blue-50 rounded-lg p-3 border-l-4 border-blue-400"
    >
      <ExclamationCircleIcon class="w-5 h-5 flex-shrink-0 mt-0.5" />
      <div>
        <p class="font-medium">{{ t("repository.local.hint") }}</p>
        <p class="mt-1 text-xs text-blue-600">
          {{ t("repository.local.hintDetail") }}
        </p>
      </div>
    </div>

    <div>
      <label class="block text-sm font-medium text-foreground mb-1"
        >{{ t("repository.boundSyncProxy") }} *</label
      >
      <select
        :value="newRepo.bound_node || ''"
        @change="
          $emit(
            'handleProxySelect',
            ($event.target as HTMLSelectElement).value,
          )
        "
        :class="[
          'w-full px-3 py-2 text-sm border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2',
          formErrors.bound_node
            ? 'border-red-300 focus:ring-red-500'
            : 'border-border focus:ring-blue-500',
        ]"
      >
        <option class="bg-background/50" value="">
          {{ t("repository.selectSyncProxy") }}
        </option>
        <option
          class="bg-background/50"
          v-for="proxy in availableSyncProxies"
          :key="proxy.id"
          :value="proxy.id"
        >
          {{ proxy.name }} ({{ proxy.hostname || proxy.id }}) -
          {{ t("proxies.status.online") }}
        </option>
      </select>
      <p
        v-if="formErrors.bound_node"
        class="mt-1 text-xs text-red-500 dark:text-red-400"
      >
        {{ formErrors.bound_node }}
      </p>
      <p class="text-xs text-foreground-secondary mt-1">
        {{ t("repository.boundSyncProxyHint") }}
      </p>
      <p
        v-if="availableSyncProxies.length === 0"
        class="text-xs text-amber-600 mt-1"
      >
        {{
          t("repository.noOnlineSyncProxy") ||
          "No online Sync Proxies available. Please ensure your Sync Proxy is connected."
        }}
      </p>
    </div>

    <div v-if="newRepo.bound_node" class="space-y-2">
      <label class="block text-sm font-medium text-foreground">
        {{ t("repository.local.manualPath") }} *
      </label>
      <div class="flex gap-2">
        <input
          v-model="newRepo.local_config.path"
          @input="
            $emit('clearLocalPathCheck');
            $emit('clearError', 'path');
          "
          type="text"
          :placeholder="t('repository.local.pathPlaceholder')"
          :class="[
            'flex-1 px-3 py-2 text-sm border rounded-lg bg-background/50 text-foreground placeholder-foreground-muted focus:outline-none focus:ring-2',
            formErrors.path
              ? 'border-red-300 focus:ring-red-500'
              : 'border-border focus:ring-blue-500',
          ]"
        />
        <button
          type="button"
          @click="$emit('checkLocalPath')"
          :disabled="checkingLocalPath || !newRepo.local_config.path.trim()"
          class="px-4 py-2 text-sm font-medium rounded-lg border border-border bg-background-secondary text-foreground hover:bg-hover disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{
            checkingLocalPath
              ? t("repository.local.checkingPath")
              : t("repository.local.checkPath")
          }}
        </button>
      </div>
      <p class="text-xs text-foreground-secondary">
        {{ t("repository.local.manualPathHint") }}
      </p>
      <div
        v-if="localPathCheckResult"
        :class="[
          'rounded-lg border p-3 text-sm',
          localPathCheckResult.success !== false &&
          localPathCheckResult.writable !== false
            ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-300'
            : 'border-red-200 bg-red-50 text-red-700 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-300',
        ]"
      >
        <div class="flex items-start gap-2">
          <CheckCircleIcon
            v-if="
              localPathCheckResult.success !== false &&
              localPathCheckResult.writable !== false
            "
            class="w-5 h-5 flex-shrink-0"
          />
          <XCircleIcon v-else class="w-5 h-5 flex-shrink-0" />
          <div class="space-y-1">
            <p class="font-medium">
              {{
                localPathCheckResult.success !== false &&
                localPathCheckResult.writable !== false
                  ? t("repository.local.pathCheckSuccess")
                  : t("repository.local.pathCheckFailed")
              }}
            </p>
            <p v-if="localPathCheckResult.message">
              {{ localPathCheckResult.message }}
            </p>
            <p v-if="localPathCheckResult.error">
              {{ localPathCheckResult.error }}
            </p>
            <p
              v-if="
                localPathCheckResult.writable !== null &&
                localPathCheckResult.writable !== undefined
              "
              class="text-xs"
            >
              {{
                localPathCheckResult.writable
                  ? t("repository.local.writable")
                  : t("repository.local.notWritable")
              }}
            </p>
            <p
              v-if="localPathCheckResult.space_info?.total_bytes"
              class="text-xs"
            >
              {{ t("repository.local.spaceInfo") }}:
              {{
                formatBytes(localPathCheckResult.space_info.used_bytes || 0)
              }}
              /
              {{ formatBytes(localPathCheckResult.space_info.total_bytes || 0) }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <div
      v-if="newRepo.bound_node"
      class="bg-background/50 rounded-lg border border-border"
    >
      <div class="px-3 py-2 border-b border-border flex items-center justify-between">
        <div class="flex items-center gap-2 text-sm">
          <FolderIcon class="w-4 h-4 text-foreground-muted" />
          <span class="text-foreground-secondary">{{
            t("repository.local.selectDirectory")
          }}</span>
        </div>
        <button
          v-if="currentPath !== '/'"
          @click="$emit('navigateUp')"
          class="text-xs text-blue-600 hover:text-blue-700 dark:hover:text-blue-300"
        >
          {{ t("repository.local.goUp") }}
        </button>
      </div>

      <div class="px-3 py-2 border-b border-border">
        <code class="text-sm text-foreground dark:text-slate-200">{{
          currentPath || "/"
        }}</code>
      </div>

      <div v-if="isLoadingDirectories" class="flex items-center justify-center py-8">
        <div
          class="w-6 h-6 border-2 border-blue-200 border-t-blue-600 rounded-full animate-spin"
        />
      </div>

      <div v-else class="max-h-48 overflow-y-auto">
        <div
          v-if="proxyDirectories.length === 0"
          class="py-6 text-center text-sm text-foreground-secondary"
        >
          {{ t("repository.local.noSubdirectories") }}
        </div>
        <button
          v-for="dir in proxyDirectories"
          :key="dir"
          @click="$emit('navigateToDirectory', dir)"
          class="w-full px-3 py-2 flex items-center gap-2 hover:bg-hover/50 text-left text-sm"
        >
          <FolderIcon class="w-4 h-4 text-yellow-500" />
          <span class="text-foreground dark:text-slate-200">{{ dir }}</span>
          <ChevronRightIcon class="w-4 h-4 text-foreground-muted ml-auto" />
        </button>
      </div>

      <div class="px-3 py-2 border-t border-border">
        <button
          @click="$emit('selectCurrentPath')"
          class="w-full py-2 text-sm text-blue-600 hover:text-blue-700 dark:hover:text-blue-300 font-medium"
        >
          {{ t("repository.local.useCurrentPath") }}
        </button>
      </div>
    </div>

    <div
      v-if="newRepo.local_config.path"
      class="flex items-center gap-2 p-3 bg-green-50 dark:bg-green-900/30 rounded-lg"
    >
      <CheckCircleIcon class="w-5 h-5 text-green-600" />
      <span class="text-sm text-green-700 dark:text-green-400"
        >{{ t("repository.local.selectedPath") }}:
        <code class="bg-green-100 dark:bg-green-800/50 px-1 rounded">{{
          newRepo.local_config.path
        }}</code></span
      >
    </div>

    <p v-if="formErrors.path" class="text-xs text-red-500 dark:text-red-400">
      {{ formErrors.path }}
    </p>

    <div
      v-if="availableSyncProxies.length === 0"
      class="flex items-start gap-2 p-3 bg-amber-50 dark:bg-amber-900/30 rounded-lg border border-amber-200 dark:border-amber-800"
    >
      <ExclamationCircleIcon
        class="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0"
      />
      <div>
        <p class="text-sm font-medium text-amber-700">
          {{ t("repository.local.noSyncProxy") }}
        </p>
        <p class="text-xs text-amber-600 dark:text-amber-400 mt-1">
          {{ t("repository.local.noSyncProxyHint") }}
        </p>
      </div>
    </div>
  </div>
</template>
