<script setup lang="ts">
import { useI18n } from "vue-i18n";

const model = defineModel<Record<string, any>>({ required: true });
defineProps<{ metrics: string[] }>();
const { t } = useI18n();
</script>

<template>
  <div class="grid gap-4 md:grid-cols-3">
    <label class="space-y-2">
      <span class="text-sm font-medium text-foreground">{{
        t("alertsCenter.form.metric")
      }}</span>
      <select
        v-model="model.metric_key"
        class="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20">
        <option v-for="metric in metrics" :key="metric" :value="metric">
          {{ metric }}
        </option>
      </select>
    </label>
    <label class="space-y-2">
      <span class="text-sm font-medium text-foreground">{{
        t("alertsCenter.form.operator")
      }}</span>
      <select
        v-model="model.operator"
        class="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20">
        <option
          v-for="op in ['>', '>=', '<', '<=', '==', '!=']"
          :key="op"
          :value="op">
          {{ op }}
        </option>
      </select>
    </label>
    <label class="space-y-2">
      <span class="text-sm font-medium text-foreground">{{
        t("alertsCenter.form.threshold")
      }}</span>
      <input
        v-model.number="model.threshold"
        type="number"
        class="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" />
    </label>
    <label class="space-y-2">
      <span class="text-sm font-medium text-foreground">{{
        t("alertsCenter.form.unit")
      }}</span>
      <input
        v-model="model.unit"
        class="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" />
    </label>
    <label class="space-y-2">
      <span class="text-sm font-medium text-foreground">{{
        t("alertsCenter.form.durationSeconds")
      }}</span>
      <select
        v-model.number="model.duration_seconds"
        class="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20">
        <option :value="300">
          {{ t("alertsCenter.duration.minutes", { count: 5 }) }}
        </option>
        <option :value="600">
          {{ t("alertsCenter.duration.minutes", { count: 10 }) }}
        </option>
        <option :value="1800">
          {{ t("alertsCenter.duration.minutes", { count: 30 }) }}
        </option>
      </select>
    </label>
    <label class="space-y-2">
      <span class="text-sm font-medium text-foreground">{{
        t("alertsCenter.form.evaluationIntervalSeconds")
      }}</span>
      <select
        v-model.number="model.evaluation_interval_seconds"
        class="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20">
        <option :value="60">
          {{ t("alertsCenter.duration.minutes", { count: 1 }) }}
        </option>
        <option :value="300">
          {{ t("alertsCenter.duration.minutes", { count: 5 }) }}
        </option>
      </select>
    </label>
  </div>
</template>
