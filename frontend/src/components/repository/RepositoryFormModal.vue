<script setup lang="ts">
import { useI18n } from "vue-i18n";
import RepositoryLocalConfigSection from "@/components/repository/RepositoryLocalConfigSection.vue";
import RepositoryNasConfigSection from "@/components/repository/RepositoryNasConfigSection.vue";
import RepositoryS3ConfigSection from "@/components/repository/RepositoryS3ConfigSection.vue";
import type { ProxyNode } from "@/types/proxy";

defineProps<{
  isEditMode: boolean;
  newRepo: any;
  formErrors: Record<string, string>;
  repoTypes: Array<Record<string, any>>;
  isFormValid: boolean;
  availableSyncProxies: ProxyNode[];
  s3BucketList: Array<{ name: string; creation_date?: string; size?: number }>;
  isLoadingBuckets: boolean;
  bucketListError: string;
  checkingBucketName: boolean;
  bucketNameAvailable: boolean | null;
  bucketNameMessage: string;
  proxyDirectories: string[];
  currentPath: string;
  isLoadingDirectories: boolean;
  checkingLocalPath: boolean;
  localPathCheckResult: any;
  formatBytes: (bytes: number) => string;
}>();

const emit = defineEmits<{
  close: [];
  reset: [];
  submit: [];
  clearError: [field: string];
  fetchBucketList: [];
  checkBucketNameAvailability: [];
  handleProxySelect: [proxyId: string];
  checkLocalPath: [];
  clearLocalPathCheck: [];
  navigateUp: [];
  navigateToDirectory: [directory: string];
  selectCurrentPath: [];
}>();

const { t } = useI18n();

function closeModal() {
  emit("close");
  emit("reset");
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/50" @click="closeModal" />
      <div
        class="relative modal-surface rounded-2xl shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col"
      >
        <div
          class="px-6 py-4 border-b border-border flex items-center justify-between flex-shrink-0"
        >
          <h2 class="text-lg font-semibold text-foreground">
            {{
              isEditMode
                ? t("repository.form.editRepository")
                : t("repository.form.addRepository")
            }}
          </h2>
          <button
            class="p-1 hover:bg-background-tertiary/50 rounded-lg"
            @click="closeModal"
          >
            <svg
              class="w-5 h-5 text-foreground-muted"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div class="px-6 py-4 border-b border-border flex-shrink-0">
          <label class="block text-sm font-medium text-foreground mb-3">
            {{ t("repository.form.repositoryType") }}
          </label>
          <div class="grid grid-cols-3 gap-3">
            <button
              v-for="type in repoTypes"
              :key="type.value"
              :disabled="isEditMode"
              :class="[
                'flex flex-col items-center gap-2 p-3 rounded-xl border-2 transition-all',
                isEditMode ? 'cursor-not-allowed opacity-60' : '',
                newRepo.repo_type === type.value
                  ? 'border-blue-500 dark:border-blue-400 bg-background/50 shadow-sm'
                  : 'border-border bg-background/50 hover:border-border-secondary dark:hover:border-slate-500',
              ]"
              @click="!isEditMode && (newRepo.repo_type = type.value)"
            >
              <div
                :class="[
                  'w-9 h-9 rounded-lg flex items-center justify-center dark:bg-opacity-50',
                  type.color === 'orange'
                    ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400'
                    : type.color === 'purple'
                      ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400'
                      : 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
                ]"
              >
                <component :is="type.icon" class="w-5 h-5" />
              </div>
              <span class="text-xs font-medium text-foreground dark:text-slate-200">
                {{ type.label }}
              </span>
            </button>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto p-6 space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-foreground mb-1">
                {{ t("common.name") }} *
              </label>
              <input
                v-model="newRepo.name"
                type="text"
                :placeholder="t('repository.form.namePlaceholder')"
                :class="[
                  'w-full px-3 py-2 text-sm border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2',
                  formErrors.name
                    ? 'border-red-300 focus:ring-red-500'
                    : 'border-border focus:ring-blue-500',
                ]"
                @input="emit('clearError', 'name')"
              />
              <p
                v-if="formErrors.name"
                class="mt-1 text-xs text-red-500 dark:text-red-400"
              >
                {{ formErrors.name }}
              </p>
            </div>
            <div>
              <label class="block text-sm font-medium text-foreground mb-1">
                {{ t("common.description") }}
              </label>
              <input
                v-model="newRepo.description"
                type="text"
                :placeholder="t('repository.form.descPlaceholder')"
                class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-foreground mb-1">
                {{ t("repository.form.storageQuota") }}
                <span class="text-xs text-foreground-muted font-normal ml-1">
                  ({{ t("repository.form.quotaUnit") }})
                </span>
              </label>
              <input
                v-model.number="newRepo.quota"
                type="number"
                min="0"
                :placeholder="t('repository.form.quotaPlaceholder')"
                class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p class="mt-1 text-xs text-foreground-muted">
                {{ t("repository.form.quotaHint") }}
              </p>
            </div>

            <div>
              <label
                class="flex items-center gap-2 text-sm font-medium text-foreground mb-2"
              >
                <input
                  v-model="newRepo.quota_enabled"
                  type="checkbox"
                  class="rounded border-border-secondary text-blue-600 focus:ring-blue-500"
                />
                {{ t("repository.form.quotaEnabled") }}
              </label>
              <div
                v-if="newRepo.quota_enabled"
                class="flex items-center gap-2 mt-2"
              >
                <span class="text-sm text-foreground-secondary">
                  {{ t("repository.form.quotaThreshold") }}:
                </span>
                <input
                  v-model.number="newRepo.quota_warning_threshold"
                  type="number"
                  min="50"
                  max="100"
                  class="w-16 px-2 py-1 text-sm border border-border rounded bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <span class="text-xs text-foreground-muted">%</span>
                <p class="text-xs text-foreground-muted">
                  {{ t("repository.form.quotaThresholdHint") }}
                </p>
              </div>
            </div>
          </div>

          <RepositoryS3ConfigSection
            v-if="newRepo.repo_type === 's3'"
            :new-repo="newRepo"
            :form-errors="formErrors"
            :available-sync-proxies="availableSyncProxies"
            :is-edit-mode="isEditMode"
            :s3-bucket-list="s3BucketList"
            :is-loading-buckets="isLoadingBuckets"
            :bucket-list-error="bucketListError"
            :checking-bucket-name="checkingBucketName"
            :bucket-name-available="bucketNameAvailable"
            :bucket-name-message="bucketNameMessage"
            @clear-error="emit('clearError', $event)"
            @fetch-bucket-list="emit('fetchBucketList')"
            @check-bucket-name-availability="
              emit('checkBucketNameAvailability')
            "
          />

          <RepositoryNasConfigSection
            v-if="newRepo.repo_type === 'nas'"
            :new-repo="newRepo"
            :form-errors="formErrors"
            :available-sync-proxies="availableSyncProxies"
            :is-edit-mode="isEditMode"
            @clear-error="emit('clearError', $event)"
          />

          <RepositoryLocalConfigSection
            v-if="newRepo.repo_type === 'local'"
            :new-repo="newRepo"
            :form-errors="formErrors"
            :available-sync-proxies="availableSyncProxies"
            :proxy-directories="proxyDirectories"
            :current-path="currentPath"
            :is-loading-directories="isLoadingDirectories"
            :checking-local-path="checkingLocalPath"
            :local-path-check-result="localPathCheckResult"
            :format-bytes="formatBytes"
            @handle-proxy-select="emit('handleProxySelect', $event)"
            @check-local-path="emit('checkLocalPath')"
            @clear-error="emit('clearError', $event)"
            @clear-local-path-check="emit('clearLocalPathCheck')"
            @navigate-up="emit('navigateUp')"
            @navigate-to-directory="emit('navigateToDirectory', $event)"
            @select-current-path="emit('selectCurrentPath')"
          />
        </div>

        <div
          class="px-6 py-4 rounded-2xl border-t border-border flex justify-end gap-3 flex-shrink-0 bg-card"
        >
          <button
            class="px-4 py-2 text-sm text-foreground-secondary border border-border rounded-lg hover:bg-hover/50 transition-colors"
            @click="closeModal"
          >
            {{ t("common.cancel") }}
          </button>
          <button
            :disabled="!isFormValid"
            :class="[
              'px-4 py-2 text-sm rounded-lg transition-colors',
              isFormValid
                ? 'text-white bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600'
                : 'text-foreground-secondary bg-slate-200 dark:bg-slate-600 cursor-not-allowed',
            ]"
            @click="emit('submit')"
          >
            {{ isEditMode ? t("common.save") : t("common.create") }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
