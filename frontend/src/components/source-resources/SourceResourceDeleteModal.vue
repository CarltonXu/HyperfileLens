<script setup lang="ts">
import { useI18n } from "vue-i18n";
import type { SourceResource } from "@/types/sourceResource";

defineProps<{
  resource: SourceResource;
}>();

defineEmits<{
  close: [];
  confirm: [];
}>();

const { t } = useI18n();
</script>

<template>
  <div class="fixed inset-0 z-50 overflow-y-auto">
    <div class="flex min-h-full items-center justify-center p-4">
      <div class="fixed inset-0 bg-black/50" @click="$emit('close')" />
      <div class="relative w-full max-w-sm rounded-xl modal-surface shadow-xl">
        <div class="p-6">
          <h2 class="mb-2 text-lg font-semibold text-foreground">
            {{ t("sourceResources.deleteConfirm") }}
          </h2>
          <p class="mb-4 text-sm text-foreground-secondary dark:text-slate-400">
            {{
              t("sourceResources.deleteConfirmDesc", { name: resource.name })
            }}
          </p>
          <div class="flex justify-end gap-3">
            <button
              class="rounded-lg px-4 py-2 text-sm text-foreground-secondary hover:bg-background-tertiary"
              @click="$emit('close')"
            >
              {{ t("common.cancel") }}
            </button>
            <button
              class="rounded-lg bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-700"
              @click="$emit('confirm')"
            >
              {{ t("common.delete") }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
