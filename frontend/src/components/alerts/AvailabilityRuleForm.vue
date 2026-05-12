<script setup lang="ts">
import { useI18n } from "vue-i18n";

const model = defineModel<Record<string, any>>({ required: true });
const { t } = useI18n();
</script>

<template>
  <div class="grid gap-4 md:grid-cols-3">
    <label class="space-y-2">
      <span class="text-sm font-medium text-foreground">{{
        t("alertsCenter.form.checkType")
      }}</span>
      <select
        v-model="model.check_type"
        class="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20">
        <option value="heartbeat">heartbeat</option>
        <option value="connection">connection</option>
        <option value="api_health">api_health</option>
      </select>
    </label>
    <label class="space-y-2">
      <span class="text-sm font-medium text-foreground">{{
        t("alertsCenter.form.timeoutSeconds")
      }}</span>
      <input
        v-model.number="model.timeout_seconds"
        type="number"
        class="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" />
    </label>
    <label class="space-y-2">
      <span class="text-sm font-medium text-foreground">{{
        t("alertsCenter.form.durationSeconds")
      }}</span>
      <input
        v-model.number="model.duration_seconds"
        type="number"
        class="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" />
    </label>
  </div>
</template>
