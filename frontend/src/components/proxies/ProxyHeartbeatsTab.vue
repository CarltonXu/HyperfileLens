<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import { ArrowPathIcon, SignalIcon } from "@heroicons/vue/24/outline";

interface HeartbeatStats {
  heartbeats_24h?: number;
  expected_24h?: number;
  missed_heartbeats?: number;
}

interface HeartbeatRecord {
  id: string;
  timestamp: string;
  cpu_usage?: number | null;
  memory_usage?: number | null;
  disk_usage?: number | null;
}

const props = defineProps<{
  heartbeats: HeartbeatRecord[];
  stats: HeartbeatStats | null | undefined;
  interval: number;
}>();

const emit = defineEmits<{
  "update:interval": [value: number];
  "set-auto-refresh": [interval: number];
  refresh: [];
}>();

const { t } = useI18n();

const refreshInterval = computed({
  get: () => props.interval,
  set: (value: number) => emit("update:interval", Number(value)),
});

function calculateHeartbeatRate(
  stats: HeartbeatStats | null | undefined,
): number {
  if (!stats || !stats.expected_24h || stats.expected_24h === 0) return 100;
  return Math.round(((stats.heartbeats_24h || 0) / stats.expected_24h) * 100);
}
</script>

<template>
  <div class="space-y-4">
    <div
      class="flex items-center justify-between bg-background-secondary rounded-xl p-3"
    >
      <div class="flex items-center gap-2">
        <SignalIcon class="w-4 h-4 text-foreground-secondary" />
        <span class="text-sm text-foreground-secondary">
          {{ t("proxies.monitoring.autoRefresh") }}
        </span>
      </div>
      <div class="flex items-center gap-2">
        <select
          v-model="refreshInterval"
          @change="emit('set-auto-refresh', refreshInterval)"
          class="text-sm bg-background text-foreground border border-border rounded-lg px-2 py-1 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option :value="0">{{ t("proxies.monitoring.refreshOff") }}</option>
          <option :value="10">{{ t("proxies.monitoring.refresh10s") }}</option>
          <option :value="30">{{ t("proxies.monitoring.refresh30s") }}</option>
          <option :value="60">{{ t("proxies.monitoring.refresh1m") }}</option>
          <option :value="300">{{ t("proxies.monitoring.refresh5m") }}</option>
        </select>
        <button
          @click="emit('refresh')"
          class="p-1.5 text-foreground-secondary hover:text-indigo-600 hover:bg-card rounded-lg"
        >
          <ArrowPathIcon class="w-4 h-4" />
        </button>
      </div>
    </div>

    <div class="grid grid-cols-4 gap-4">
      <div class="bg-background-secondary rounded-xl p-4">
        <p class="text-xs text-foreground-secondary">
          {{ t("proxies.heartbeats.totalHeartbeats") }}
        </p>
        <p class="text-2xl font-bold text-foreground mt-1">
          {{ stats?.heartbeats_24h || 0 }}
        </p>
        <p class="text-xs text-foreground-muted mt-1">
          24h {{ t("proxies.heartbeats.totalHeartbeats") }}
        </p>
      </div>
      <div class="bg-background-secondary rounded-xl p-4">
        <p class="text-xs text-foreground-secondary">
          {{ t("proxies.heartbeats.expectedHeartbeats") }}
        </p>
        <p class="text-2xl font-bold text-indigo-600 mt-1">
          {{ stats?.expected_24h || 0 }}
        </p>
        <p class="text-xs text-foreground-muted mt-1">
          24h {{ t("proxies.heartbeats.expectedHeartbeats") }}
        </p>
      </div>
      <div class="bg-background-secondary rounded-xl p-4">
        <p class="text-xs text-foreground-secondary">
          {{ t("proxies.heartbeats.missedHeartbeats") }}
        </p>
        <p
          class="text-2xl font-bold"
          :class="
            (stats?.missed_heartbeats || 0) > 0
              ? 'text-red-600'
              : 'text-foreground'
          "
        >
          {{ stats?.missed_heartbeats || 0 }}
        </p>
        <p class="text-xs text-foreground-muted mt-1">
          {{ t("proxies.heartbeats.missedHeartbeats") }}
        </p>
      </div>
      <div class="bg-background-secondary rounded-xl p-4">
        <p class="text-xs text-foreground-secondary">
          {{ t("proxies.heartbeats.heartbeatRate") }}
        </p>
        <p
          class="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1"
        >
          {{ calculateHeartbeatRate(stats) }}%
        </p>
        <p class="text-xs text-foreground-muted mt-1">
          {{ t("proxies.heartbeats.heartbeatRate") }}
        </p>
      </div>
    </div>

    <div
      v-if="heartbeats.length === 0"
      class="bg-background-secondary rounded-xl p-8 text-center"
    >
      <SignalIcon class="w-16 h-16 mx-auto mb-4 text-slate-300" />
      <p class="text-foreground-secondary font-medium">
        {{ t("proxies.detail.noHeartbeats") }}
      </p>
      <p class="text-sm text-foreground-muted mt-1">
        {{ t("proxies.detail.noHeartbeatsHint") }}
      </p>
    </div>
    <div v-else class="space-y-2">
      <div
        v-for="heartbeat in heartbeats"
        :key="heartbeat.id"
        class="bg-background-secondary rounded-lg p-3"
      >
        <div class="flex items-center justify-between">
          <span class="text-xs text-foreground-secondary">
            {{ new Date(heartbeat.timestamp).toLocaleString() }}
          </span>
          <div class="flex items-center gap-3 text-xs">
            <span class="text-indigo-600">
              CPU: {{ (heartbeat.cpu_usage || 0).toFixed(1) }}%
            </span>
            <span class="text-emerald-600 dark:text-emerald-400">
              Mem: {{ (heartbeat.memory_usage || 0).toFixed(1) }}%
            </span>
            <span class="text-amber-600 dark:text-amber-400">
              Disk: {{ (heartbeat.disk_usage || 0).toFixed(1) }}%
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
