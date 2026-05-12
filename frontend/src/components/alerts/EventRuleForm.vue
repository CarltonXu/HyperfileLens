<script setup lang="ts">
import { computed, watch } from "vue";
import { useI18n } from "vue-i18n";

const model = defineModel<Record<string, any>>({ required: true });
const { t } = useI18n();

const eventTypesByCategory: Record<string, string[]> = {
  user: [
    "user_created",
    "user_deleted",
    "user_disabled",
    "user_enabled",
    "password_changed",
    "user_role_changed",
    "login_success",
    "login_failed",
    "logout",
  ],
  license: [
    "license_added",
    "license_updated",
    "license_expired",
    "license_near_expiration",
    "license_capacity_exceeded",
  ],
  repository: [
    "repository_created",
    "repository_deleted",
    "repository_updated",
    "repository_unreachable",
    "repository_readonly",
    "repository_capacity_low",
  ],
  configuration: [
    "configuration_changed",
    "notification_channel_changed",
    "alert_policy_changed",
    "repository_config_changed",
    "proxy_config_changed",
  ],
  security: [
    "multiple_login_failures",
    "api_token_created",
    "api_token_deleted",
    "permission_changed",
    "mfa_disabled",
  ],
};

const categories = Object.keys(eventTypesByCategory);

const availableEventTypes = computed(() => {
  const category = model.value.event_category || "user";
  return eventTypesByCategory[category] || [];
});

watch(
  () => model.value.event_category,
  (category) => {
    if (!category || !eventTypesByCategory[category]) {
      model.value.event_category = "user";
      return;
    }

    const available = new Set(eventTypesByCategory[category]);
    const selected = (model.value.event_types || []).filter((item: string) =>
      available.has(item),
    );
    model.value.event_types = selected.length
      ? selected
      : [eventTypesByCategory[category][0]];
  },
  { immediate: true },
);
</script>

<template>
  <div class="grid gap-4 md:grid-cols-2">
    <label class="space-y-2">
      <span class="text-sm font-medium text-foreground">{{
        t("alertsCenter.form.eventCategory")
      }}</span>
      <select
        v-model="model.event_category"
        class="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20">
        <option v-for="item in categories" :key="item" :value="item">
          {{ item }}
        </option>
      </select>
    </label>
    <label class="space-y-2 md:col-span-2">
      <span class="text-sm font-medium text-foreground">{{
        t("alertsCenter.form.eventTypes")
      }}</span>
      <select
        v-model="model.event_types"
        multiple
        class="min-h-32 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20">
        <option v-for="item in availableEventTypes" :key="item" :value="item">
          {{ item }}
        </option>
      </select>
      <p class="text-xs text-foreground-secondary">
        {{ t("alertsCenter.common.holdToSelectEvents") }}
      </p>
    </label>
  </div>
</template>
