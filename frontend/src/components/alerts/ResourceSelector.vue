<script setup lang="ts">
import { useI18n } from "vue-i18n";

const resourceType = defineModel<string>("resourceType", { required: true });
const scope = defineModel<string>("scope", { required: true });
const resourceIds = defineModel<string[]>("resourceIds", { required: true });

defineProps<{
  resourceTypes: Array<{ value: string; label: string }>;
  resources?: Array<{ id: string; name: string; status?: string }>;
  loading?: boolean;
  disabled?: boolean;
}>();

const emit = defineEmits<{ refresh: [] }>();
const { t } = useI18n();
</script>

<template>
  <div class="grid gap-4 md:grid-cols-3">
    <label class="space-y-2">
      <span class="text-sm font-medium text-foreground">{{
        t("alertsCenter.form.resourceType")
      }}</span>
      <select
        v-model="resourceType"
        :disabled="disabled"
        class="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-60">
        <option
          v-for="item in resourceTypes"
          :key="item.value"
          :value="item.value">
          {{ item.label }}
        </option>
      </select>
    </label>
    <label class="space-y-2">
      <span class="text-sm font-medium text-foreground">{{
        t("alertsCenter.form.scope")
      }}</span>
      <select
        v-model="scope"
        :disabled="disabled"
        class="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-60">
        <option value="all">{{ t("alertsCenter.values.all") }}</option>
        <option value="selected">
          {{ t("alertsCenter.values.selected") }}
        </option>
      </select>
    </label>
    <div class="space-y-2">
      <div class="flex items-center justify-between gap-2">
        <span class="text-sm font-medium text-foreground">{{
          t("alertsCenter.form.monitorResources")
        }}</span>
        <button
          type="button"
          :disabled="disabled || scope === 'all' || loading"
          @click="emit('refresh')"
          class="text-xs font-medium text-primary hover:underline disabled:cursor-not-allowed disabled:text-foreground-muted disabled:no-underline">
          {{
            loading
              ? t("alertsCenter.common.loading")
              : t("alertsCenter.common.refresh")
          }}
        </button>
      </div>
      <select
        v-model="resourceIds"
        multiple
        :disabled="disabled || scope === 'all'"
        class="min-h-10 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-60">
        <option v-if="!resources?.length" disabled value="">
          {{
            scope === "all"
              ? t("alertsCenter.common.allResourcesSelected")
              : t("alertsCenter.common.noResourcesAvailable")
          }}
        </option>
        <option v-for="item in resources" :key="item.id" :value="item.id">
          {{ item.name }}{{ item.status ? ` · ${item.status}` : "" }}
        </option>
      </select>
      <p class="text-xs text-foreground-secondary">
        {{
          scope === "all"
            ? t("alertsCenter.common.allResourcesSelected")
            : t("alertsCenter.common.holdToSelect")
        }}
      </p>
    </div>
  </div>
</template>
