<script setup lang="ts">
import { useI18n } from "vue-i18n";

const model = defineModel<Record<string, any>>({ required: true });
const { t } = useI18n();
</script>

<template>
  <div class="grid gap-4 md:grid-cols-2">
    <label class="space-y-2">
      <span class="text-sm font-medium text-foreground">{{
        t("alertsCenter.form.jobType")
      }}</span>
      <select
        v-model="model.job_type"
        class="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20">
        <option
          v-for="item in ['backup', 'sync', 'restore', 'verify', 'cleanup']"
          :key="item"
          :value="item">
          {{ item }}
        </option>
      </select>
    </label>
    <label class="space-y-2">
      <span class="text-sm font-medium text-foreground">{{
        t("alertsCenter.form.eventType")
      }}</span>
      <select
        v-model="model.event_type"
        class="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20">
        <option
          v-for="item in [
            'job_failed',
            'job_timeout',
            'retry_exceeded',
            'partial_success',
          ]"
          :key="item"
          :value="item">
          {{ item }}
        </option>
      </select>
    </label>
    <label class="space-y-2 md:col-span-2">
      <span class="text-sm font-medium text-foreground">{{
        t("alertsCenter.form.consecutiveFailures")
      }}</span>
      <input
        v-model.number="model.consecutive_failures"
        type="number"
        min="1"
        class="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" />
    </label>
  </div>
</template>
