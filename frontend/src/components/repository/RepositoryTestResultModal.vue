<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  CheckCircleIcon,
  CircleStackIcon,
  PencilIcon,
  SignalIcon,
  XCircleIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline";

defineProps<{
  result: {
    success: boolean;
    message: string;
    details?: any;
  } | null;
  formatBytes: (bytes: number) => string;
}>();

const emit = defineEmits<{
  close: [];
}>();

const { t } = useI18n();
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/50" @click="emit('close')" />
      <div
        class="relative modal-surface rounded-xl shadow-2xl w-full max-w-lg overflow-hidden"
      >
        <div
          class="flex items-center justify-between px-6 py-4 border-b border-border"
        >
          <div class="flex items-center gap-3">
            <div
              :class="[
                'w-10 h-10 rounded-full flex items-center justify-center',
                result?.success
                  ? 'bg-emerald-100 dark:bg-emerald-900/30'
                  : 'bg-red-100 dark:bg-red-900/30',
              ]"
            >
              <CheckCircleIcon
                v-if="result?.success"
                class="w-6 h-6 text-emerald-600 dark:text-emerald-400"
              />
              <XCircleIcon
                v-else
                class="w-6 h-6 text-red-600 dark:text-red-400"
              />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-foreground">
                {{ t("repository.connectionTestResult") }}
              </h3>
              <p class="text-sm text-foreground-secondary">
                {{ result?.message }}
              </p>
            </div>
          </div>
          <button
            @click="emit('close')"
            class="p-2 hover:bg-background-tertiary/50 rounded-lg transition-colors"
          >
            <XMarkIcon class="w-5 h-5 text-foreground-muted" />
          </button>
        </div>

        <div v-if="result?.details" class="p-6">
          <div class="space-y-4">
            <div
              v-if="result.details.connectivity"
              class="bg-background-secondary rounded-lg p-4"
            >
              <div class="flex items-center gap-2 mb-2">
                <SignalIcon
                  class="w-5 h-5 text-emerald-600 dark:text-emerald-400"
                />
                <h4 class="text-sm font-medium text-foreground">
                  {{ t("repository.connectivity") }}
                </h4>
              </div>
              <div class="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p class="text-xs text-foreground-secondary">
                    {{ t("repository.reachable") }}
                  </p>
                  <p
                    :class="[
                      'font-medium',
                      result.details.connectivity.reachable
                        ? 'text-emerald-600'
                        : 'text-red-600',
                    ]"
                  >
                    {{
                      result.details.connectivity.reachable
                        ? t("common.yes")
                        : t("common.no")
                    }}
                  </p>
                </div>
                <div>
                  <p class="text-xs text-foreground-secondary">
                    {{ t("repository.responseTime") }}
                  </p>
                  <p class="font-medium text-foreground">
                    {{ result.details.connectivity.response_time || 0 }}ms
                  </p>
                </div>
                <div
                  v-if="result.details.connectivity.error"
                  class="col-span-2"
                >
                  <p class="text-xs text-foreground-secondary">
                    {{ t("common.error") }}
                  </p>
                  <p class="font-medium text-red-600">
                    {{ result.details.connectivity.error }}
                  </p>
                </div>
              </div>
            </div>

            <div
              v-if="result.details.write_test"
              class="bg-background-secondary rounded-lg p-4"
            >
              <div class="flex items-center gap-2 mb-2">
                <PencilIcon class="w-5 h-5 text-blue-600 dark:text-blue-400" />
                <h4 class="text-sm font-medium text-foreground">
                  {{ t("repository.writeTest") }}
                </h4>
              </div>
              <div class="grid grid-cols-3 gap-3 text-sm">
                <div>
                  <p class="text-xs text-foreground-secondary">
                    {{ t("repository.writable") }}
                  </p>
                  <p
                    :class="[
                      'font-medium',
                      result.details.write_test.writable
                        ? 'text-emerald-600'
                        : 'text-red-600',
                    ]"
                  >
                    {{
                      result.details.write_test.writable
                        ? t("common.yes")
                        : t("common.no")
                    }}
                  </p>
                </div>
                <div>
                  <p class="text-xs text-foreground-secondary">
                    {{ t("repository.writeSpeed") }}
                  </p>
                  <p class="font-medium text-foreground">
                    {{ result.details.write_test.write_speed || 0 }} MB/s
                  </p>
                </div>
                <div>
                  <p class="text-xs text-foreground-secondary">
                    {{ t("repository.readSpeed") }}
                  </p>
                  <p class="font-medium text-foreground">
                    {{ result.details.write_test.read_speed || 0 }} MB/s
                  </p>
                </div>
                <div v-if="result.details.write_test.error" class="col-span-3">
                  <p class="text-xs text-foreground-secondary">
                    {{ t("common.error") }}
                  </p>
                  <p class="font-medium text-red-600">
                    {{ result.details.write_test.error }}
                  </p>
                </div>
              </div>
            </div>

            <div
              v-if="result.details.space_info"
              class="bg-background-secondary rounded-lg p-4"
            >
              <div class="flex items-center gap-2 mb-2">
                <CircleStackIcon
                  class="w-5 h-5 text-purple-600 dark:text-purple-400"
                />
                <h4 class="text-sm font-medium text-foreground">
                  {{ t("repository.storageInfo") }}
                </h4>
              </div>
              <div class="grid grid-cols-3 gap-3 text-sm mb-3">
                <div>
                  <p class="text-xs text-foreground-secondary">
                    {{ t("repository.total") }}
                  </p>
                  <p class="font-medium text-foreground">
                    {{
                      formatBytes(result.details.space_info.total_bytes || 0)
                    }}
                  </p>
                </div>
                <div>
                  <p class="text-xs text-foreground-secondary">
                    {{ t("repository.used") }}
                  </p>
                  <p class="font-medium text-foreground">
                    {{ formatBytes(result.details.space_info.used_bytes || 0) }}
                  </p>
                </div>
                <div>
                  <p class="text-xs text-foreground-secondary">
                    {{ t("repository.free") }}
                  </p>
                  <p class="font-medium text-foreground">
                    {{ formatBytes(result.details.space_info.free_bytes || 0) }}
                  </p>
                </div>
              </div>
              <div
                class="w-full bg-slate-200 dark:bg-slate-600 dark:bg-slate-600 rounded-full h-2"
              >
                <div
                  class="bg-purple-600 h-2 rounded-full transition-all duration-500"
                  :style="{
                    width: `${result.details.space_info.total_bytes ? ((result.details.space_info.used_bytes / result.details.space_info.total_bytes) * 100).toFixed(1) : 0}%`,
                  }"
                />
              </div>
              <p class="text-xs text-foreground-secondary text-center mt-1">
                {{
                  result.details.space_info.total_bytes
                    ? (
                        (result.details.space_info.used_bytes /
                          result.details.space_info.total_bytes) *
                        100
                      ).toFixed(1)
                    : 0
                }}% {{ t("repository.used") }}
              </p>
            </div>
          </div>
        </div>

        <div class="px-6 py-4 border-t border-border flex justify-end">
          <button
            @click="emit('close')"
            class="px-4 py-2 text-sm text-foreground-secondary border border-border rounded-lg hover:bg-hover/50"
          >
            {{ t("common.close") }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
