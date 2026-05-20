<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { ClockIcon, ShieldCheckIcon } from "@heroicons/vue/24/outline";

defineProps<{
  policies: Array<Record<string, any>>;
  selectedPolicy: Record<string, any> | null;
  policyScheduleSummary: string;
  policyRetentionSummary: string;
  retentionFields: ReadonlyArray<{ key: string; label: string }>;
}>();

const form = defineModel<any>("form", { required: true });
const { t } = useI18n();
</script>

<template>
  <section class="rounded-lg border border-border bg-card p-4">
    <div class="mb-2 flex items-center gap-2">
      <ClockIcon class="h-5 w-5 text-primary" />
      <h3 class="font-semibold text-foreground">
        {{ t("backupTasks.detail.scheduleRetention") }}
      </h3>
    </div>
    <p class="mb-4 text-xs text-foreground-secondary">
      {{ t("backupTasks.edit.sections.scheduleRetentionDesc") }}
    </p>
    <div class="space-y-5">
      <div>
        <label class="block text-sm font-medium text-foreground mb-1">
          {{ t("backupTasks.form.policy") }}
        </label>
        <select
          v-model="form.schedule"
          @change="
            ((form.retention_mode = form.schedule ? 'policy' : 'custom'),
            (form.override_schedule = false))
          "
          class="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        >
          <option :value="null">
            {{ t("backupTasks.form.noPolicy") }}
          </option>
          <option
            v-for="policy in policies"
            :key="policy.id"
            :value="policy.id"
          >
            {{ policy.name }}
          </option>
        </select>
        <p class="mt-1 text-xs text-foreground-muted">
          {{ t("backupTasks.edit.fieldDescriptions.policy") }}
        </p>
      </div>

      <div v-if="selectedPolicy" class="grid grid-cols-1 gap-3 md:grid-cols-2">
        <div
          class="rounded-lg border border-border bg-background/50 p-3 text-sm"
        >
          <p class="text-xs text-foreground-muted">
            {{ t("backupTasks.policyOverrides.schedule") }}
          </p>
          <p class="mt-1 font-medium text-foreground">
            {{ policyScheduleSummary }}
          </p>
        </div>
        <div
          class="rounded-lg border border-border bg-background/50 p-3 text-sm"
        >
          <p class="text-xs text-foreground-muted">
            {{ t("backupTasks.policyOverrides.retention") }}
          </p>
          <p class="mt-1 font-medium text-foreground">
            {{ policyRetentionSummary }}
          </p>
        </div>
      </div>

      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div
          class="rounded-lg border border-border bg-background/30 p-4 space-y-4"
        >
          <div class="flex items-center gap-2">
            <ClockIcon class="h-5 w-5 text-primary" />
            <p class="text-sm font-semibold text-foreground">
              {{ t("backupTasks.form.schedule") }}
            </p>
          </div>
          <template v-if="selectedPolicy">
            <label class="flex items-start gap-2 text-sm text-foreground">
              <input
                :checked="!form.override_schedule"
                type="radio"
                class="mt-1 border-border"
                @change="form.override_schedule = false"
              />
              <span>
                <span class="font-medium">
                  {{ t("backupTasks.policyOverrides.usePolicySchedule") }}
                </span>
                <span class="mt-1 block text-xs text-foreground-muted">
                  {{ policyScheduleSummary }}
                </span>
              </span>
            </label>
            <label class="flex items-start gap-2 text-sm text-foreground">
              <input
                :checked="form.override_schedule"
                type="radio"
                class="mt-1 border-border"
                @change="form.override_schedule = true"
              />
              <span>
                <span class="font-medium">
                  {{ t("backupTasks.policyOverrides.overrideSchedule") }}
                </span>
                <span class="mt-1 block text-xs text-foreground-muted">
                  {{ t("backupTasks.policyOverrides.overrideScheduleDesc") }}
                </span>
              </span>
            </label>
          </template>

          <div v-if="!selectedPolicy || form.override_schedule">
            <label class="mb-1 block text-sm font-medium text-foreground">
              {{ t("policies.schedule.title") }}
            </label>
            <select
              v-model="form.schedule_mode"
              class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="manual">
                {{ t("policies.scheduleModes.manual") }}
              </option>
              <option value="interval">
                {{ t("policies.scheduleModes.interval") }}
              </option>
              <option value="time">
                {{ t("policies.scheduleModes.time") }}
              </option>
              <option value="cron">
                {{ t("policies.scheduleModes.cron") }}
              </option>
            </select>
            <p class="mt-1 text-xs text-foreground-muted">
              {{
                t(`policies.schedule.modeDescriptions.${form.schedule_mode}`)
              }}
            </p>
          </div>

          <div
            v-if="
              (!selectedPolicy || form.override_schedule) &&
              form.schedule_mode === 'interval'
            "
          >
            <label class="block text-sm font-medium text-foreground mb-1">
              {{ t("policies.schedule.interval") }}
            </label>
            <input
              v-model="form.interval"
              placeholder="24h"
              class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <p class="mt-1 text-xs text-foreground-muted">
              {{ t("policies.schedule.intervalDesc") }}
            </p>
          </div>

          <div
            v-if="
              (!selectedPolicy || form.override_schedule) &&
              form.schedule_mode === 'time'
            "
          >
            <label class="block text-sm font-medium text-foreground mb-1">
              {{ t("policies.schedule.timeOfDay") }}
            </label>
            <input
              v-model="form.time_of_day"
              type="time"
              class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <p class="mt-1 text-xs text-foreground-muted">
              {{ t("policies.schedule.timeOfDayDesc") }}
            </p>
          </div>

          <div
            v-if="
              (!selectedPolicy || form.override_schedule) &&
              form.schedule_mode === 'cron'
            "
          >
            <label class="block text-sm font-medium text-foreground mb-1">
              {{ t("policies.schedule.cron") }}
            </label>
            <input
              v-model="form.cron_expression"
              placeholder="0 2 * * *"
              class="w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-sm placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <p class="mt-1 text-xs text-foreground-muted">
              {{ t("policies.schedule.cronDesc") }}
            </p>
          </div>
        </div>

        <div
          class="rounded-lg border border-border bg-background/30 p-4 space-y-4"
        >
          <div class="flex items-center gap-2">
            <ShieldCheckIcon class="h-5 w-5 text-primary" />
            <p class="text-sm font-semibold text-foreground">
              {{ t("backupTasks.retention.title") }}
            </p>
          </div>
          <template v-if="selectedPolicy">
            <label class="flex items-center gap-2 text-sm text-foreground">
              <input
                v-model="form.retention_mode"
                type="radio"
                value="policy"
                class="border-border"
              />
              {{ t("backupTasks.policyOverrides.usePolicyRetention") }}
            </label>
            <label class="flex items-center gap-2 text-sm text-foreground">
              <input
                v-model="form.retention_mode"
                type="radio"
                value="custom"
                class="border-border"
              />
              {{ t("backupTasks.policyOverrides.overrideRetention") }}
            </label>
          </template>
          <p v-else class="text-sm text-foreground-secondary">
            {{ t("backupTasks.policyOverrides.taskRetentionDesc") }}
          </p>
          <div
            v-if="form.retention_mode === 'custom' || !selectedPolicy"
            class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3"
          >
            <label
              v-for="field in retentionFields"
              :key="field.key"
              class="block"
            >
              <span class="text-xs text-foreground-secondary">
                {{ t(`backupTasks.retention.${field.label}`) }}
              </span>
              <input
                v-model.number="form[field.key]"
                type="number"
                min="0"
                class="mt-1 w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <p class="mt-1 text-[11px] leading-4 text-foreground-muted">
                {{ t(`backupTasks.retention.${field.label}Desc`) }}
              </p>
            </label>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
