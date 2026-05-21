<script setup lang="ts">
import { useI18n } from "vue-i18n";
import type { SourceResourceStats } from "@/types/sourceResource";

defineProps<{
  stats: SourceResourceStats | null;
}>();

const { t } = useI18n();
</script>

<template>
  <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
    <div class="rounded-xl border border-border bg-card p-4 shadow-sm">
      <p class="text-xs text-foreground-secondary">
        {{ t("sourceResources.stats.total") }}
      </p>
      <p class="mt-1 text-xl font-bold text-foreground">
        {{ stats?.total_resources || (stats as any)?.total || 0 }}
      </p>
    </div>
    <div class="rounded-xl border border-border bg-card p-4 shadow-sm">
      <p class="text-xs text-foreground-secondary">
        {{ t("sourceResources.stats.active") }}
      </p>
      <p class="mt-1 text-xl font-bold text-emerald-600">
        {{ stats?.active_resources || (stats as any)?.active || 0 }}
      </p>
    </div>
    <div class="rounded-xl border border-border bg-card p-4 shadow-sm">
      <p class="text-xs text-foreground-secondary">
        {{ t("sourceResources.stats.mounted") }}
      </p>
      <p class="mt-1 text-xl font-bold text-indigo-600">
        {{ stats?.mounted_resources || (stats as any)?.mounted || 0 }}
      </p>
    </div>
    <div class="rounded-xl border border-border bg-card p-4 shadow-sm">
      <p class="text-xs text-foreground-secondary">
        {{ t("sourceResources.stats.error") }}
      </p>
      <p class="mt-1 text-xl font-bold text-red-600">
        {{ stats?.error_resources || (stats as any)?.error || 0 }}
      </p>
    </div>
  </div>
</template>
