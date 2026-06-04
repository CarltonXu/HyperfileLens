<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import {
  ArrowDownTrayIcon,
  CheckCircleIcon,
  CircleStackIcon,
  ClipboardDocumentIcon,
  ComputerDesktopIcon,
  CpuChipIcon,
  DocumentDuplicateIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  KeyIcon,
  ServerIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline";

interface InstallData {
  name: string;
  role: "agent" | "sync";
  os: string;
  labels: string[];
  newLabel: string;
}

interface InstallResult {
  proxy_id: string;
  name: string;
  role: string;
  install_token: string;
  api_token: string;
  install_command: string;
  linux_command?: string;
  macos_command?: string;
  windows_command: string;
  config_yaml: string;
  expires_at: string;
}

const props = defineProps<{
  installStep: number;
  installData: InstallData;
  installResult: InstallResult | null;
  isGeneratingInstall: boolean;
  command: string;
}>();

const emit = defineEmits<{
  close: [];
  "update:installStep": [value: number];
  addLabel: [];
  removeLabel: [label: string];
  generate: [];
  downloadConfig: [];
  copyCommand: [command: string];
  done: [];
}>();

const { t } = useI18n();

const step = computed({
  get: () => props.installStep,
  set: (value: number) => emit("update:installStep", value),
});

function selectRole(role: "agent" | "sync") {
  props.installData.role = role;
  if (role === "sync") {
    props.installData.os = "linux";
  }
  step.value = 2;
}
</script>

<template>
  <div
    class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 overflow-y-auto"
  >
    <div class="modal-surface rounded-2xl shadow-xl max-w-2xl w-full my-8">
      <div class="flex items-center justify-between p-5 border-b border-border">
        <div>
          <h2 class="text-lg font-semibold text-foreground">
            {{ t("proxies.install.title") }}
          </h2>
          <p class="text-sm text-foreground-secondary mt-1">
            {{ t("proxies.install.subtitle") }}
          </p>
        </div>
        <button
          @click="emit('close')"
          class="p-1.5 text-foreground-muted hover:text-foreground-secondary hover:bg-hover rounded-lg"
        >
          <XMarkIcon class="w-5 h-5" />
        </button>
      </div>

      <div class="p-5">
        <div v-if="step === 1" class="space-y-6">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <button
              @click="selectRole('agent')"
              :class="[
                'p-6 rounded-xl border-2 text-left transition-all',
                installData.role === 'agent'
                  ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/30'
                  : 'border-border hover:border-slate-300 dark:hover:border-slate-600',
              ]"
            >
              <div
                class="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center mb-4"
              >
                <ComputerDesktopIcon class="w-6 h-6 text-white" />
              </div>
              <h3 class="font-semibold text-foreground">
                {{ t("proxies.roles.agent") }}
              </h3>
              <p class="text-sm text-foreground-secondary mt-2">
                {{ t("proxies.install.agentDescription") }}
              </p>

              <div class="mt-4 pt-4 border-t border-border">
                <p class="text-xs font-medium text-foreground-secondary mb-2">
                  {{ t("proxies.install.requirements") }}
                </p>
                <div class="space-y-1.5 text-xs text-foreground-secondary">
                  <div class="flex items-center gap-2">
                    <ComputerDesktopIcon
                      class="w-3.5 h-3.5 text-foreground-muted"
                    />
                    <span>{{ t("proxies.install.agentOS") }}</span>
                  </div>
                  <div class="flex items-center gap-2">
                    <CpuChipIcon class="w-3.5 h-3.5 text-foreground-muted" />
                    <span>{{ t("proxies.install.agentCPU") }}</span>
                  </div>
                  <div class="flex items-center gap-2">
                    <CircleStackIcon
                      class="w-3.5 h-3.5 text-foreground-muted"
                    />
                    <span>{{ t("proxies.install.agentMemory") }}</span>
                  </div>
                  <div class="flex items-center gap-2">
                    <ServerIcon class="w-3.5 h-3.5 text-foreground-muted" />
                    <span>{{ t("proxies.install.agentDisk") }}</span>
                  </div>
                </div>
              </div>
            </button>

            <button
              @click="selectRole('sync')"
              :class="[
                'p-6 rounded-xl border-2 text-left transition-all',
                installData.role === 'sync'
                  ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/30'
                  : 'border-border hover:border-slate-300 dark:hover:border-slate-600',
              ]"
            >
              <div
                class="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center mb-4"
              >
                <CircleStackIcon class="w-6 h-6 text-white" />
              </div>
              <h3 class="font-semibold text-foreground">
                {{ t("proxies.roles.sync") }}
              </h3>
              <p class="text-sm text-foreground-secondary mt-2">
                {{ t("proxies.install.syncDescription") }}
              </p>

              <div class="mt-4 pt-4 border-t border-border">
                <p class="text-xs font-medium text-foreground-secondary mb-2">
                  {{ t("proxies.install.requirements") }}
                </p>
                <div class="space-y-1.5 text-xs text-foreground-secondary">
                  <div class="flex items-center gap-2">
                    <ComputerDesktopIcon
                      class="w-3.5 h-3.5 text-foreground-muted"
                    />
                    <span>{{ t("proxies.install.syncOS") }}</span>
                  </div>
                  <div class="flex items-center gap-2">
                    <CpuChipIcon class="w-3.5 h-3.5 text-foreground-muted" />
                    <span>{{ t("proxies.install.syncCPU") }}</span>
                  </div>
                  <div class="flex items-center gap-2">
                    <CircleStackIcon
                      class="w-3.5 h-3.5 text-foreground-muted"
                    />
                    <span>{{ t("proxies.install.syncMemory") }}</span>
                  </div>
                  <div class="flex items-center gap-2">
                    <ServerIcon class="w-3.5 h-3.5 text-foreground-muted" />
                    <span>{{ t("proxies.install.syncDisk") }}</span>
                  </div>
                </div>
              </div>
            </button>
          </div>

          <div
            class="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-lg p-4 flex items-start gap-3"
          >
            <InformationCircleIcon
              class="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0"
            />
            <div class="text-sm text-blue-700 dark:text-blue-300">
              <p class="font-medium">{{ t("proxies.install.infoTitle") }}</p>
              <p class="mt-1">{{ t("proxies.install.infoDescription") }}</p>
            </div>
          </div>
        </div>

        <div v-if="step === 2" class="space-y-5">
          <div>
            <label class="block text-sm font-medium text-foreground mb-1">
              {{ t("proxies.install.proxyName") }}
            </label>
            <input
              v-model="installData.name"
              type="text"
              required
              :placeholder="t('proxies.install.namePlaceholder')"
              class="w-full px-4 py-2.5 border border-border rounded-lg bg-background text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div v-if="installData.role === 'agent'">
            <label class="block text-sm font-medium text-foreground mb-1">
              {{ t("proxies.install.targetOS") }}
            </label>
            <div class="grid grid-cols-3 gap-3">
              <button
                v-for="os in ['linux', 'windows', 'macos']"
                :key="os"
                @click="installData.os = os"
                :class="[
                  'px-4 py-3 rounded-lg border-2 text-sm font-medium transition-all',
                  installData.os === os
                    ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400'
                    : 'border-border bg-background text-foreground-secondary hover:border-slate-300 dark:hover:border-slate-500',
                ]"
              >
                {{ t(`proxies.install.os.${os}`) }}
              </button>
            </div>
          </div>

          <div
            v-else
            class="bg-purple-50 dark:bg-purple-900/30 border border-purple-200 dark:border-purple-800 rounded-lg p-4"
          >
            <div class="flex items-center gap-3">
              <div
                class="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center"
              >
                <ComputerDesktopIcon
                  class="w-5 h-5 text-purple-600 dark:text-purple-400"
                />
              </div>
              <div>
                <p
                  class="text-sm font-medium text-purple-800 dark:text-purple-200"
                >
                  {{ t("proxies.install.syncFixedOS") }}
                </p>
                <p class="text-xs text-purple-600 dark:text-purple-400">
                  {{ t("proxies.install.syncFixedOSNote") }}
                </p>
              </div>
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-foreground mb-1">
              {{ t("proxies.install.labels") }}
            </label>
            <div class="flex gap-2 mb-2">
              <input
                v-model="installData.newLabel"
                type="text"
                :placeholder="t('proxies.install.labelPlaceholder')"
                class="flex-1 px-3 py-2 border border-border rounded-lg bg-background text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-indigo-500"
                @keyup.enter="emit('addLabel')"
              />
              <button
                @click="emit('addLabel')"
                class="px-4 py-2 text-sm font-medium text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800 rounded-lg hover:bg-indigo-50 dark:hover:bg-indigo-900/30 transition-colors"
              >
                {{ t("common.add") }}
              </button>
            </div>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="label in installData.labels"
                :key="label"
                class="inline-flex items-center gap-1 px-3 py-1 bg-background-tertiary text-foreground-secondary rounded-full text-sm"
              >
                {{ label }}
                <button
                  @click="emit('removeLabel', label)"
                  class="hover:text-red-500"
                >
                  <XMarkIcon class="w-3.5 h-3.5" />
                </button>
              </span>
            </div>
          </div>

          <div class="flex justify-between pt-4">
            <button
              @click="step = 1"
              class="px-4 py-2 text-sm font-medium text-foreground-secondary bg-background-tertiary rounded-lg hover:bg-slate-200 transition-colors"
            >
              {{ t("common.back") }}
            </button>
            <button
              @click="emit('generate')"
              :disabled="!installData.name || isGeneratingInstall"
              class="px-6 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {{
                isGeneratingInstall
                  ? t("proxies.install.generating")
                  : t("proxies.install.generateCommand")
              }}
            </button>
          </div>
        </div>

        <div v-if="step === 3 && installResult" class="space-y-5">
          <div
            class="bg-emerald-50 dark:bg-emerald-900/30 border border-emerald-200 dark:border-emerald-800 rounded-lg p-4 flex items-start gap-3"
          >
            <CheckCircleIcon class="w-5 h-5 text-emerald-500 mt-0.5" />
            <div>
              <p
                class="text-sm font-medium text-emerald-800 dark:text-emerald-200"
              >
                {{ t("proxies.install.ready") }}
              </p>
              <p class="text-sm text-emerald-600 dark:text-emerald-400 mt-1">
                {{ t("proxies.install.readyDescription") }}
              </p>
            </div>
          </div>

          <div class="space-y-4">
            <div class="bg-background-secondary rounded-lg p-4">
              <div class="flex items-center gap-2 mb-3">
                <span
                  class="w-6 h-6 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 text-xs font-bold flex items-center justify-center"
                  >1</span
                >
                <span class="text-sm font-medium text-foreground">{{
                  t("proxies.install.step1Title")
                }}</span>
              </div>
              <p class="text-xs text-foreground-secondary mb-3">
                {{ t("proxies.install.step1Desc") }}
              </p>
              <div class="relative">
                <pre
                  class="bg-slate-900 text-slate-100 p-4 rounded-lg text-sm overflow-x-auto whitespace-pre-wrap font-mono"
                  >{{ command }}</pre
                >
                <div class="absolute top-2 right-2 flex gap-2">
                  <button
                    @click="emit('downloadConfig')"
                    class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-300 bg-slate-700 rounded-lg hover:bg-slate-600"
                  >
                    <ArrowDownTrayIcon class="w-3.5 h-3.5" />
                    {{ t("proxies.install.downloadConfig") }}
                  </button>
                  <button
                    @click="emit('copyCommand', command)"
                    class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-500"
                  >
                    <ClipboardDocumentIcon class="w-3.5 h-3.5" />
                    {{ t("common.copy") }}
                  </button>
                </div>
              </div>
            </div>

            <div
              class="bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 rounded-lg p-4"
            >
              <div class="flex items-start gap-3">
                <ExclamationTriangleIcon
                  class="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0"
                />
                <div class="flex-1">
                  <p
                    class="text-sm font-medium text-amber-800 dark:text-amber-200"
                  >
                    {{ t("proxies.install.credentialsTitle") }}
                  </p>
                  <p class="text-xs text-amber-600 dark:text-amber-400 mt-1">
                    {{ t("proxies.install.credentialsDesc") }}
                  </p>
                </div>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="modal-surface border border-border rounded-lg p-4">
                <div class="flex items-center gap-2 mb-2">
                  <span
                    class="w-6 h-6 rounded-full bg-background-tertiary text-foreground-secondary text-xs font-bold flex items-center justify-center"
                    >ID</span
                  >
                  <span class="text-sm font-medium text-foreground">{{
                    t("proxies.install.proxyId")
                  }}</span>
                </div>
                <p class="text-xs text-foreground-secondary mb-2">
                  {{ t("proxies.install.proxyIdDesc") }}
                </p>
                <div
                  class="flex items-center gap-2 bg-background-secondary rounded px-3 py-2"
                >
                  <p class="text-sm font-mono text-foreground flex-1 truncate">
                    {{ installResult.proxy_id }}
                  </p>
                  <button
                    @click="emit('copyCommand', installResult.proxy_id)"
                    class="text-foreground-muted hover:text-foreground-secondary"
                  >
                    <DocumentDuplicateIcon class="w-4 h-4" />
                  </button>
                </div>
              </div>
              <div class="modal-surface border border-border rounded-lg p-4">
                <div class="flex items-center gap-2 mb-2">
                  <span
                    class="w-6 h-6 rounded-full bg-background-tertiary text-foreground-secondary text-xs font-bold flex items-center justify-center"
                  >
                    <KeyIcon class="w-3.5 h-3.5" />
                  </span>
                  <span class="text-sm font-medium text-foreground">{{
                    t("proxies.install.apiToken")
                  }}</span>
                </div>
                <p class="text-xs text-foreground-secondary mb-2">
                  {{ t("proxies.install.apiTokenDesc") }}
                </p>
                <div
                  class="flex items-center gap-2 bg-background-secondary rounded px-3 py-2"
                >
                  <p class="text-sm font-mono text-foreground flex-1 break-all">
                    {{ installResult.api_token || "N/A" }}
                  </p>
                  <button
                    @click="emit('copyCommand', installResult.api_token)"
                    class="text-foreground-muted hover:text-foreground-secondary flex-shrink-0"
                  >
                    <DocumentDuplicateIcon class="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div class="flex justify-between pt-4">
            <button
              @click="step = 2"
              class="px-4 py-2 text-sm font-medium text-foreground-secondary bg-background-tertiary rounded-lg hover:bg-slate-200 transition-colors"
            >
              {{ t("common.back") }}
            </button>
            <button
              @click="emit('done')"
              class="px-6 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
            >
              {{ t("proxies.install.done") }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
