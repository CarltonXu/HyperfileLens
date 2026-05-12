<script setup lang="ts">
import { useI18n } from "vue-i18n";

const model = defineModel<Record<string, any>>({ required: true });
const { t } = useI18n();
</script>

<template>
  <div class="space-y-4">
    <div
      class="flex items-center justify-between rounded-lg border border-border bg-background px-3 py-2.5">
      <div>
        <p class="text-sm font-medium text-foreground">
          {{ t("alertsCenter.form.enableAutoRecovery") }}
        </p>
        <p class="mt-0.5 text-xs text-foreground-secondary">
          {{ t("alertsCenter.form.enableAutoRecoveryDesc") }}
        </p>
      </div>
      <button
        type="button"
        role="switch"
        :aria-checked="model.enabled"
        @click="model.enabled = !model.enabled"
        class="relative h-6 w-11 rounded-full transition-colors"
        :class="
          model.enabled
            ? 'bg-primary'
            : 'bg-background-tertiary border border-border'
        ">
        <span
          class="absolute left-0 top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform"
          :class="model.enabled ? 'translate-x-5' : 'translate-x-0.5'" />
      </button>
    </div>

    <div
      class="grid gap-4 md:grid-cols-3"
      :class="!model.enabled && 'opacity-50'">
      <label class="space-y-2">
        <span class="text-sm font-medium text-foreground">{{
          t("alertsCenter.form.recoveryCondition")
        }}</span>
        <select
          v-model="model.recovery_condition"
          :disabled="!model.enabled"
          class="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:cursor-not-allowed">
          <option value="below_threshold">below_threshold</option>
          <option value="heartbeat_restored">heartbeat_restored</option>
          <option value="next_success">next_success</option>
          <option value="service_restored">service_restored</option>
        </select>
      </label>
      <label class="space-y-2">
        <span class="text-sm font-medium text-foreground">{{
          t("alertsCenter.form.operator")
        }}</span>
        <select
          v-model="model.operator"
          :disabled="!model.enabled"
          class="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:cursor-not-allowed">
          <option
            v-for="op in ['<', '<=', '>', '>=', '==', '!=']"
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
          :disabled="!model.enabled"
          type="number"
          class="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:cursor-not-allowed" />
      </label>
      <label class="space-y-2">
        <span class="text-sm font-medium text-foreground">{{
          t("alertsCenter.form.duration")
        }}</span>
        <select
          v-model.number="model.duration_seconds"
          :disabled="!model.enabled"
          class="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:cursor-not-allowed">
          <option :value="120">
            {{ t("alertsCenter.duration.minutes", { count: 2 }) }}
          </option>
          <option :value="180">
            {{ t("alertsCenter.duration.minutes", { count: 3 }) }}
          </option>
          <option :value="300">
            {{ t("alertsCenter.duration.minutes", { count: 5 }) }}
          </option>
          <option :value="600">
            {{ t("alertsCenter.duration.minutes", { count: 10 }) }}
          </option>
        </select>
      </label>
    </div>
  </div>
</template>
