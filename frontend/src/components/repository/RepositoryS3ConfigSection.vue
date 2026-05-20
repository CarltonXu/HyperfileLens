<script setup lang="ts">
import { useI18n } from "vue-i18n";
import type { ProxyNode } from "@/types/proxy";
import {
  ArrowPathIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  FolderIcon,
  InformationCircleIcon,
  XCircleIcon,
} from "@heroicons/vue/24/outline";
import {
  ExclamationTriangleIcon,
  PlusCircleIcon,
} from "@heroicons/vue/24/solid";

defineProps<{
  newRepo: {
    bound_node: string | null;
    s3_config: {
      endpoint: string;
      bucket: string;
      region: string;
      prefix: string;
      access_key: string;
      secret_key: string;
      use_tls: boolean;
      url_style: "virtual" | "path";
      bucket_mode: "existing" | "new";
    };
  };
  formErrors: Record<string, string>;
  availableSyncProxies: ProxyNode[];
  isEditMode: boolean;
  s3BucketList: Array<{ name: string; creation_date?: string; size?: number }>;
  isLoadingBuckets: boolean;
  bucketListError: string;
  checkingBucketName: boolean;
  bucketNameAvailable: boolean | null;
  bucketNameMessage: string;
}>();

defineEmits<{
  clearError: [field: string];
  fetchBucketList: [];
  checkBucketNameAvailability: [];
}>();

const { t } = useI18n();
</script>

<template>
  <div class="space-y-4 p-4 rounded-xl border border-border">
    <div
      class="flex items-start gap-2 text-sm text-orange-700 dark:text-orange-400 bg-orange-50 rounded-lg p-3 border-l-4 border-orange-400"
    >
      <ExclamationCircleIcon class="w-5 h-5 flex-shrink-0 mt-0.5" />
      <div>
        <p class="font-medium">{{ t("repository.s3.hint") }}</p>
        <p class="mt-1 text-xs text-orange-600">
          {{ t("repository.s3.hintDetail") }}
        </p>
      </div>
    </div>

    <div>
      <label class="block text-sm font-medium text-foreground mb-1"
        >{{ t("repository.boundSyncProxy") }} *</label
      >
      <select
        v-model="newRepo.bound_node"
        :class="[
          'w-full px-3 py-2 text-sm border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2',
          formErrors.bound_node
            ? 'border-red-300 focus:ring-red-500'
            : 'border-border focus:ring-blue-500',
        ]"
        @change="$emit('clearError', 'bound_node')"
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
          {{
            proxy.is_online
              ? t("proxies.status.online")
              : t("proxies.status.offline")
          }}
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

    <div class="p-3 bg-background/50 rounded-lg border border-border">
      <h4 class="text-sm font-medium text-foreground mb-3">
        {{ t("repository.s3.credentials") }}
      </h4>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-foreground mb-1"
            >{{ t("repository.s3.endpoint") }} *</label
          >
          <input
            v-model="newRepo.s3_config.endpoint"
            type="text"
            placeholder="https://s3.amazonaws.com"
            :class="[
              'w-full px-3 py-2 text-sm border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2',
              formErrors.endpoint
                ? 'border-red-300 focus:ring-red-500'
                : 'border-border focus:ring-blue-500',
            ]"
            @input="$emit('clearError', 'endpoint')"
          />
          <p class="text-xs text-foreground-secondary mt-1">
            {{ t("repository.s3.endpointHint") }}
          </p>
          <p
            v-if="formErrors.endpoint"
            class="mt-1 text-xs text-red-500 dark:text-red-400"
          >
            {{ formErrors.endpoint }}
          </p>
        </div>
        <div>
          <label class="block text-sm font-medium text-foreground mb-1"
            >{{ t("repository.s3.region") }}</label
          >
          <input
            v-model="newRepo.s3_config.region"
            type="text"
            placeholder="us-east-1"
            class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground mb-1"
            >{{ t("repository.s3.urlStyle") }}</label
          >
          <select
            v-model="newRepo.s3_config.url_style"
            class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option class="bg-background/50" value="virtual">
              {{ t("repository.s3.urlStyleVirtual") }}
            </option>
            <option class="bg-background/50" value="path">
              {{ t("repository.s3.urlStylePath") }}
            </option>
          </select>
          <p class="text-xs text-foreground-secondary mt-1">
            {{ t("repository.s3.urlStyleHint") }}
          </p>
        </div>

        <div class="flex items-center justify-between py-2">
          <div>
            <label
              class="block text-sm font-medium text-foreground dark:text-slate-200"
              >{{ t("repository.s3.useTLS") }}</label
            >
            <p class="text-xs text-foreground-secondary">
              {{ t("repository.s3.useTLSHint") }}
            </p>
          </div>
          <button
            type="button"
            @click="newRepo.s3_config.use_tls = !newRepo.s3_config.use_tls"
            :class="[
              'relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
              newRepo.s3_config.use_tls
                ? 'bg-blue-600'
                : 'bg-slate-200 dark:bg-slate-600',
            ]"
            role="switch"
            :aria-checked="newRepo.s3_config.use_tls"
          >
            <span
              :class="[
                'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out',
                newRepo.s3_config.use_tls ? 'translate-x-5' : 'translate-x-0',
              ]"
            ></span>
          </button>
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground mb-1"
            >{{ t("repository.s3.accessKey") }} *</label
          >
          <input
            v-model="newRepo.s3_config.access_key"
            type="text"
            placeholder="AKIAIOSFODNN7EXAMPLE"
            :class="[
              'w-full px-3 py-2 text-sm border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2',
              formErrors.access_key
                ? 'border-red-300 focus:ring-red-500'
                : 'border-border focus:ring-blue-500',
            ]"
            @input="$emit('clearError', 'access_key')"
          />
          <p
            v-if="formErrors.access_key"
            class="mt-1 text-xs text-red-500 dark:text-red-400"
          >
            {{ formErrors.access_key }}
          </p>
        </div>
        <div>
          <label class="block text-sm font-medium text-foreground mb-1">
            {{ t("repository.s3.secretKey") }}
            <span v-if="!isEditMode">*</span>
          </label>
          <input
            v-model="newRepo.s3_config.secret_key"
            type="password"
            :placeholder="
              isEditMode ? '••••••••••••••••' : '••••••••••••••••'
            "
            :class="[
              'w-full px-3 py-2 text-sm border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2',
              formErrors.secret_key
                ? 'border-red-300 focus:ring-red-500'
                : 'border-border focus:ring-blue-500',
            ]"
            @input="$emit('clearError', 'secret_key')"
          />
          <p
            v-if="isEditMode && !formErrors.secret_key"
            class="mt-1 text-xs text-foreground-secondary"
          >
            {{ t("repository.s3.secretKeyEditHint") }}
          </p>
          <p
            v-if="formErrors.secret_key"
            class="mt-1 text-xs text-red-500 dark:text-red-400"
          >
            {{ formErrors.secret_key }}
          </p>
        </div>
      </div>
    </div>

    <div class="p-3 bg-background/50 rounded-lg border border-border">
      <h4 class="text-sm font-medium text-foreground mb-3">
        {{ t("repository.s3.bucketSelection") }}
      </h4>

      <div class="mb-4">
        <div class="grid grid-cols-2 gap-3">
          <button
            @click="newRepo.s3_config.bucket_mode = 'existing'"
            :class="[
              'flex items-center justify-center gap-2 p-3 rounded-lg border-2 transition-all text-sm font-medium',
              newRepo.s3_config.bucket_mode === 'existing'
                ? 'border-orange-500 dark:border-orange-500 bg-orange-50 text-orange-700 dark:text-orange-400'
                : 'border-border text-foreground-secondary hover:border-border-secondary dark:hover:border-slate-500',
            ]"
          >
            <FolderIcon class="w-4 h-4" />
            {{ t("repository.s3.existingBucket") }}
          </button>
          <button
            @click="newRepo.s3_config.bucket_mode = 'new'"
            :class="[
              'flex items-center justify-center gap-2 p-3 rounded-lg border-2 transition-all text-sm font-medium',
              newRepo.s3_config.bucket_mode === 'new'
                ? 'border-orange-500 dark:border-orange-500 bg-orange-50 text-orange-700 dark:text-orange-400'
                : 'border-border text-foreground-secondary hover:border-border-secondary dark:hover:border-slate-500',
            ]"
          >
            <PlusCircleIcon class="w-4 h-4" />
            {{ t("repository.s3.newBucket") }}
          </button>
        </div>
      </div>

      <div v-if="newRepo.s3_config.bucket_mode === 'existing'">
        <div
          class="flex items-start gap-2 text-sm text-amber-700 bg-amber-50 rounded-lg p-3 mb-4 border border-amber-300 dark:border-amber-700 border-l-4"
        >
          <ExclamationTriangleIcon class="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div>
            <p class="font-medium">
              {{ t("repository.s3.existingBucketWarning") }}
            </p>
            <p class="mt-1 text-xs text-amber-600 dark:text-amber-400">
              {{ t("repository.s3.existingBucketWarningDetail") }}
            </p>
          </div>
        </div>

        <button
          @click="$emit('fetchBucketList')"
          :disabled="
            !newRepo.s3_config.endpoint ||
            !newRepo.s3_config.access_key ||
            !newRepo.s3_config.secret_key
          "
          :class="[
            'w-full px-4 py-2 rounded-lg text-sm font-medium transition-all mb-3',
            !newRepo.s3_config.endpoint ||
            !newRepo.s3_config.access_key ||
            !newRepo.s3_config.secret_key
              ? 'bg-background-tertiary/50 text-foreground-muted cursor-not-allowed'
              : 'bg-orange-500 text-white hover:bg-orange-600',
          ]"
        >
          <span
            v-if="isLoadingBuckets"
            class="flex items-center justify-center gap-2"
          >
            <svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
              <circle
                class="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                stroke-width="4"
              ></circle>
              <path
                class="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path>
            </svg>
            {{ t("repository.s3.loadingBuckets") }}
          </span>
          <span v-else class="flex items-center justify-center gap-2">
            <ArrowPathIcon class="w-4 h-4" />
            {{ t("repository.s3.fetchBucketList") }}
          </span>
        </button>

        <p v-if="bucketListError" class="mb-3 text-xs text-red-500 dark:text-red-400">
          {{ bucketListError }}
        </p>

        <div v-if="s3BucketList.length > 0">
          <label class="block text-sm font-medium text-foreground mb-1"
            >{{ t("repository.s3.selectBucket") }} *</label
          >
          <select
            v-model="newRepo.s3_config.bucket"
            :class="[
              'w-full px-3 py-2 text-sm border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2',
              formErrors.bucket
                ? 'border-red-300 focus:ring-red-500'
                : 'border-border focus:ring-blue-500',
            ]"
            @change="$emit('clearError', 'bucket')"
          >
            <option class="bg-background/50" value="">
              {{ t("repository.s3.selectBucketPlaceholder") }}
            </option>
            <option
              class="bg-background/50"
              v-for="bucket in s3BucketList"
              :key="bucket.name"
              :value="bucket.name"
            >
              {{ bucket.name }}
            </option>
          </select>
          <p
            v-if="formErrors.bucket"
            class="mt-1 text-xs text-red-500 dark:text-red-400"
          >
            {{ formErrors.bucket }}
          </p>
        </div>
      </div>

      <div v-if="newRepo.s3_config.bucket_mode === 'new'">
        <div
          class="flex items-start gap-2 text-sm text-foreground-secondary rounded-lg p-3 mb-4 border border-border"
        >
          <InformationCircleIcon
            class="w-5 h-5 flex-shrink-0 mt-0.5 text-foreground-muted"
          />
          <div class="text-xs space-y-1">
            <p class="font-medium text-foreground dark:text-slate-200">
              {{ t("repository.s3.bucketNameRules") }}:
            </p>
            <ul class="list-disc list-inside text-foreground-secondary space-y-0.5">
              <li>{{ t("repository.s3.bucketNameRule1") }}</li>
              <li>{{ t("repository.s3.bucketNameRule2") }}</li>
              <li>{{ t("repository.s3.bucketNameRule3") }}</li>
              <li>{{ t("repository.s3.bucketNameRule4") }}</li>
              <li>{{ t("repository.s3.bucketNameRule5") }}</li>
            </ul>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground mb-1"
            >{{ t("repository.s3.bucketName") }} *</label
          >
          <div class="relative">
            <input
              v-model="newRepo.s3_config.bucket"
              type="text"
              placeholder="my-backup-bucket"
              :class="[
                'w-full px-3 py-2 text-sm border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2 pr-24',
                formErrors.bucket
                  ? 'border-red-300 focus:ring-red-500'
                  : bucketNameAvailable === true
                    ? 'border-green-300 focus:ring-green-500'
                    : bucketNameAvailable === false
                      ? 'border-red-300 focus:ring-red-500'
                      : 'border-border focus:ring-blue-500',
              ]"
              @input="$emit('clearError', 'bucket')"
            />
            <button
              @click="$emit('checkBucketNameAvailability')"
              :disabled="!newRepo.s3_config.bucket || checkingBucketName"
              :class="[
                'absolute right-1 top-1 bottom-1 px-3 rounded text-xs font-medium transition-all',
                !newRepo.s3_config.bucket || checkingBucketName
                  ? 'bg-background-tertiary/50 text-foreground-muted cursor-not-allowed'
                  : 'bg-blue-500 text-white hover:bg-blue-600',
              ]"
            >
              {{
                checkingBucketName
                  ? t("repository.s3.checking")
                  : t("repository.s3.check")
              }}
            </button>
          </div>

          <p
            v-if="bucketNameMessage"
            :class="[
              'mt-1 text-xs flex items-center gap-1',
              bucketNameAvailable === true
                ? 'text-green-600'
                : 'text-red-500 dark:text-red-400',
            ]"
          >
            <CheckCircleIcon
              v-if="bucketNameAvailable === true"
              class="w-3 h-3"
            />
            <XCircleIcon v-else class="w-3 h-3" />
            {{ bucketNameMessage }}
          </p>
          <p
            v-if="formErrors.bucket"
            class="mt-1 text-xs text-red-500 dark:text-red-400"
          >
            {{ formErrors.bucket }}
          </p>
        </div>
      </div>
    </div>

    <div>
      <label class="block text-sm font-medium text-foreground mb-1">{{
        t("repository.s3.prefix")
      }}</label>
      <input
        v-model="newRepo.s3_config.prefix"
        type="text"
        placeholder="backups/hyperfilelens"
        class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      <p class="text-xs text-foreground-secondary mt-1">
        {{ t("repository.s3.prefixHint") }}
      </p>
    </div>
  </div>
</template>
