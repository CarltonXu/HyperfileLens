<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { ArrowPathIcon, XMarkIcon } from "@heroicons/vue/24/outline";

interface ProxyEditForm {
  name: string;
  hostname: string;
  heartbeat_interval: number;
}

defineProps<{
  form: ProxyEditForm;
  saving?: boolean;
}>();

const emit = defineEmits<{
  close: [];
  submit: [];
}>();

const { t } = useI18n();
</script>

<template>
  <div
    class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
  >
    <div class="modal-surface rounded-2xl shadow-xl max-w-lg w-full">
      <div class="flex items-center justify-between p-5 border-b border-border">
        <h2 class="text-lg font-semibold text-foreground">
          {{ t("proxies.edit.title") }}
        </h2>
        <button
          @click="emit('close')"
          :disabled="saving"
          class="p-1.5 text-foreground-muted hover:text-foreground-secondary hover:bg-hover rounded-lg"
        >
          <XMarkIcon class="w-5 h-5" />
        </button>
      </div>
      <form @submit.prevent="emit('submit')" class="p-5 space-y-4">
        <div>
          <label class="block text-sm font-medium text-foreground mb-1">
            {{ t("proxies.form.name") }}
          </label>
          <input
            v-model="form.name"
            type="text"
            required
            class="w-full px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-foreground mb-1">
            {{ t("proxies.form.hostname") }}
          </label>
          <input
            v-model="form.hostname"
            type="text"
            class="w-full px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-foreground mb-1">
            {{ t("proxies.form.heartbeatInterval") }}
          </label>
          <input
            v-model.number="form.heartbeat_interval"
            type="number"
            min="5"
            max="300"
            class="w-full px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <div class="flex justify-end gap-3 pt-4 border-t border-border">
          <button
            type="button"
            @click="emit('close')"
            :disabled="saving"
            class="px-4 py-2 text-sm font-medium text-foreground-secondary bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors disabled:cursor-wait disabled:opacity-70"
          >
            {{ t("common.cancel") }}
          </button>
          <button
            type="submit"
            :disabled="saving"
            class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors disabled:cursor-wait disabled:opacity-70"
          >
            <ArrowPathIcon v-if="saving" class="w-4 h-4 animate-spin" />
            {{ saving ? t("common.saving") : t("common.save") }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
