<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  CheckCircleIcon,
  CircleStackIcon,
  ComputerDesktopIcon,
  ServerIcon,
} from "@heroicons/vue/24/outline";
import type { ProxyStats } from "@/types/proxy";

defineProps<{
  stats: ProxyStats | null;
}>();

const { t } = useI18n();
</script>

<template>
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
    <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
      <div class="flex items-center gap-3">
        <div
          class="w-10 h-10 bg-gradient-to-br from-slate-100 to-slate-200 rounded-lg flex items-center justify-center"
        >
          <ServerIcon class="w-5 h-5 text-foreground-secondary" />
        </div>
        <div>
          <p class="text-xs text-foreground-secondary">
            {{ t("proxies.stats.total") }}
          </p>
          <p class="text-xl font-bold text-foreground">
            {{ stats?.total_proxies || 0 }}
          </p>
        </div>
      </div>
    </div>
    <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
      <div class="flex items-center gap-3">
        <div
          class="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center"
        >
          <CheckCircleIcon
            class="w-5 h-5 text-emerald-600 dark:text-emerald-400"
          />
        </div>
        <div>
          <p class="text-xs text-foreground-secondary">
            {{ t("proxies.stats.online") }}
          </p>
          <p class="text-xl font-bold text-emerald-600 dark:text-emerald-400">
            {{ stats?.online_proxies || 0 }}
          </p>
        </div>
      </div>
    </div>
    <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
      <div class="flex items-center gap-3">
        <div
          class="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center"
        >
          <ComputerDesktopIcon class="w-5 h-5 text-indigo-600" />
        </div>
        <div>
          <p class="text-xs text-foreground-secondary">
            {{ t("proxies.roles.agent") }}
          </p>
          <p class="text-xl font-bold text-foreground">
            {{ stats?.agent_proxies || 0 }}
          </p>
        </div>
      </div>
    </div>
    <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
      <div class="flex items-center gap-3">
        <div
          class="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center"
        >
          <CircleStackIcon
            class="w-5 h-5 text-purple-600 dark:text-purple-400"
          />
        </div>
        <div>
          <p class="text-xs text-foreground-secondary">
            {{ t("proxies.roles.sync") }}
          </p>
          <p class="text-xl font-bold text-foreground">
            {{ stats?.sync_proxies || 0 }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
