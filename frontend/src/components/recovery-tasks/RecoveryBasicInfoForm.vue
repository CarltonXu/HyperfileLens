<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { FolderOpenIcon } from "@heroicons/vue/24/outline";

const props = defineProps<{
  name: string;
  description?: string;
}>();

const emit = defineEmits<{
  "update:name": [value: string];
  "update:description": [value: string];
}>();

const { t } = useI18n();
</script>

<template>
  <section class="rounded-lg border border-border bg-background-secondary/40 p-4">
    <div class="flex items-start gap-3 mb-4">
      <FolderOpenIcon class="w-5 h-5 text-emerald-600 mt-0.5" />
      <div>
        <h3 class="text-sm font-semibold text-foreground">
          {{ t("recoveryTasks.wizard.basic") }}
        </h3>
        <p class="text-xs text-foreground-secondary mt-1">
          {{ t("recoveryTasks.wizard.basicHelp") }}
        </p>
      </div>
    </div>
    <div class="space-y-4">
      <div>
        <label class="block text-sm font-medium text-foreground-secondary mb-1">
          {{ t("common.name") }}
        </label>
        <input
          :value="props.name"
          type="text"
          :placeholder="t('recoveryTasks.form.namePlaceholder')"
          class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
          @input="emit('update:name', ($event.target as HTMLInputElement).value)"
        />
      </div>
      <div>
        <label class="block text-sm font-medium text-foreground-secondary mb-1">
          {{ t("common.description") }}
        </label>
        <textarea
          :value="props.description"
          rows="4"
          :placeholder="t('recoveryTasks.form.descriptionPlaceholder')"
          class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
          @input="
            emit('update:description', ($event.target as HTMLTextAreaElement).value)
          "
        />
      </div>
    </div>
  </section>
</template>
