<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  Dialog,
  DialogPanel,
  DialogTitle,
  TransitionChild,
  TransitionRoot,
} from "@headlessui/vue";
import { XMarkIcon } from "@heroicons/vue/24/outline";
import type { Tenant } from "@/types/tenant";

interface TenantFormData {
  name: string;
  slug: string;
  description: string;
  contact_email: string;
  max_users: number | null;
  max_proxies: number | null;
  max_repositories: number | null;
  max_storage_gb: number | null;
}

defineProps<{
  show: boolean;
  editingTenant: Tenant | null;
  formData: TenantFormData;
  saving: boolean;
}>();

const emit = defineEmits<{
  close: [];
  save: [];
}>();

const { t } = useI18n();
</script>

<template>
  <TransitionRoot appear :show="show" as="template">
    <Dialog as="div" class="relative z-10" @close="emit('close')">
      <TransitionChild
        as="template"
        enter="duration-300 ease-out"
        enter-from="opacity-0"
        enter-to="opacity-100"
        leave="duration-200 ease-in"
        leave-from="opacity-100"
        leave-to="opacity-0"
      >
        <div
          class="fixed inset-0 bg-slate-900/75 dark:bg-slate-900/75 transition-opacity"
        />
      </TransitionChild>

      <div class="fixed inset-0 z-10 overflow-y-auto">
        <div
          class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0"
        >
          <TransitionChild
            as="template"
            enter="duration-300 ease-out"
            enter-from="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            enter-to="opacity-100 translate-y-0 sm:scale-100"
            leave="duration-200 ease-in"
            leave-from="opacity-100 translate-y-0 sm:scale-100"
            leave-to="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
          >
            <DialogPanel
              class="relative transform overflow-hidden rounded-xl modal-surface border border-border px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6"
            >
              <div class="absolute right-0 top-0 pr-4 pt-4">
                <button
                  type="button"
                  class="rounded-lg text-foreground-muted hover:text-slate-500 dark:hover:text-slate-400 focus:outline-none"
                  @click="emit('close')"
                >
                  <XMarkIcon class="h-6 w-6" aria-hidden="true" />
                </button>
              </div>
              <div class="sm:flex sm:items-start">
                <div class="mt-3 text-center sm:mt-0 sm:text-left w-full">
                  <DialogTitle
                    as="h3"
                    class="text-base font-semibold leading-6 text-foreground"
                  >
                    {{
                      editingTenant
                        ? t("tenants.editTenant")
                        : t("tenants.createTenant")
                    }}
                  </DialogTitle>
                  <form class="mt-4 space-y-4" @submit.prevent="emit('save')">
                    <div>
                      <label
                        class="block text-sm font-medium text-foreground-secondary"
                      >
                        {{ t("tenants.tenantName") }} *
                      </label>
                      <input
                        v-model="formData.name"
                        type="text"
                        required
                        :placeholder="
                          t('tenants.tenantNamePlaceholder') || '请输入租户名称'
                        "
                        class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm"
                      />
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                      <div>
                        <label
                          class="block text-sm font-medium text-foreground-secondary"
                        >
                          {{ t("tenants.tenantSlug") }} *
                        </label>
                        <input
                          v-model="formData.slug"
                          type="text"
                          required
                          pattern="[a-z0-9-]+"
                          :placeholder="
                            t('tenants.tenantSlugPlaceholder') ||
                            '例如: my-company'
                          "
                          class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm"
                        />
                        <p class="mt-1 text-xs text-foreground-secondary">
                          {{
                            t("tenants.tenantSlugHelp") ||
                            "只能使用小写字母、数字和连字符"
                          }}
                        </p>
                      </div>
                      <div>
                        <label
                          class="block text-sm font-medium text-foreground-secondary"
                        >
                          {{ t("tenants.contactEmail") }} *
                        </label>
                        <input
                          v-model="formData.contact_email"
                          type="email"
                          required
                          :placeholder="t('tenants.contactEmailPlaceholder')"
                          class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm"
                        />
                      </div>
                    </div>
                    <div>
                      <label
                        class="block text-sm font-medium text-foreground-secondary"
                      >
                        {{ t("tenants.description") }}
                      </label>
                      <textarea
                        v-model="formData.description"
                        rows="2"
                        :placeholder="
                          t('tenants.descriptionPlaceholder') ||
                          '请输入租户描述（可选）'
                        "
                        class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm"
                      />
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                      <div>
                        <label
                          class="block text-sm font-medium text-foreground-secondary"
                        >
                          {{ t("tenants.maxUsers") }}
                        </label>
                        <input
                          v-model.number="formData.max_users"
                          type="number"
                          min="1"
                          :placeholder="t('common.unlimited') || '无限制'"
                          class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm"
                        />
                      </div>
                      <div>
                        <label
                          class="block text-sm font-medium text-foreground-secondary"
                        >
                          {{ t("tenants.maxProxies") }}
                        </label>
                        <input
                          v-model.number="formData.max_proxies"
                          type="number"
                          min="1"
                          :placeholder="t('common.unlimited') || '无限制'"
                          class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm"
                        />
                      </div>
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                      <div>
                        <label
                          class="block text-sm font-medium text-foreground-secondary"
                        >
                          {{ t("tenants.maxRepositories") }}
                        </label>
                        <input
                          v-model.number="formData.max_repositories"
                          type="number"
                          min="1"
                          :placeholder="t('common.unlimited') || '无限制'"
                          class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm"
                        />
                      </div>
                      <div>
                        <label
                          class="block text-sm font-medium text-foreground-secondary"
                        >
                          {{ t("tenants.maxStorageGb") }}
                        </label>
                        <input
                          v-model.number="formData.max_storage_gb"
                          type="number"
                          min="1"
                          :placeholder="t('common.unlimited') || '无限制'"
                          class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm"
                        />
                      </div>
                    </div>
                    <div class="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse">
                      <button
                        type="submit"
                        :disabled="saving"
                        class="inline-flex w-full justify-center rounded-lg bg-indigo-600 dark:bg-indigo-500 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 dark:hover:bg-indigo-600 sm:ml-3 sm:w-auto disabled:opacity-50 transition-colors"
                      >
                        {{ saving ? t("common.saving") : t("common.save") }}
                      </button>
                      <button
                        type="button"
                        class="mt-3 inline-flex w-full justify-center rounded-lg border border-border bg-background px-3 py-2 text-sm font-semibold text-foreground-secondary hover:bg-hover sm:mt-0 sm:w-auto transition-colors"
                        @click="emit('close')"
                      >
                        {{ t("common.cancel") }}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            </DialogPanel>
          </TransitionChild>
        </div>
      </div>
    </Dialog>
  </TransitionRoot>
</template>
