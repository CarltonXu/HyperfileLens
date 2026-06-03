<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { ArrowPathIcon, MagnifyingGlassIcon } from "@heroicons/vue/24/outline";

defineProps<{
  loading: boolean;
}>();

defineEmits<{
  refresh: [];
}>();

const search = defineModel<string>("search", { required: true });
const type = defineModel<string>("type", { required: true });
const enabled = defineModel<string>("enabled", { required: true });

const { t } = useI18n();
</script>

<template>
  <div class="flex flex-shrink-0 flex-wrap gap-3 border-b border-border p-4">
      <div class="relative min-w-[200px] flex-1">
        <MagnifyingGlassIcon
          class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-foreground-muted"
        />
        <input
          v-model="search"
          class="w-full rounded-lg border border-border bg-background py-2 pl-9 pr-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          :placeholder="t('alertsCenter.channels.searchPlaceholder')"
        />
      </div>
      <select
        v-model="type"
        class="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
      >
        <option value="">{{ t("alertsCenter.common.allTypes") }}</option>
        <option value="email">{{ t("alertsCenter.values.email") }}</option>
        <option value="webhook">{{ t("alertsCenter.values.webhook") }}</option>
        <option value="dingtalk">
          {{ t("alertsCenter.values.dingtalk") }}
        </option>
        <option value="wecom">{{ t("alertsCenter.values.wecom") }}</option>
      </select>
      <select
        v-model="enabled"
        class="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
      >
        <option value="">{{ t("alertsCenter.common.allStatus") }}</option>
        <option value="true">{{ t("alertsCenter.values.enabled") }}</option>
        <option value="false">{{ t("alertsCenter.values.disabled") }}</option>
      </select>
      <button
        class="inline-flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-hover"
        @click="$emit('refresh')"
      >
        <ArrowPathIcon :class="['h-4 w-4', loading && 'animate-spin']" />
        {{ t("alertsCenter.common.refresh") }}
      </button>
  </div>
</template>
