<script setup lang="ts">
import { useI18n } from "vue-i18n";

interface HeartbeatData {
  timestamp: string;
  cpu_usage: number | null;
  memory_usage: number | null;
  disk_usage: number | null;
  active_mounts: number;
  process_count?: number;
}

defineProps<{ heartbeats: HeartbeatData[] }>();

const { t } = useI18n();

function formatDate(dateStr: string): string {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleString();
}
</script>

<template>
  <div>
    <h4 class="text-sm font-medium text-foreground mb-3">
      {{ t("gateways.monitoring.recentHeartbeats") }}
    </h4>
    <div class="bg-background-secondary rounded-lg overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-border">
            <th class="text-left px-4 py-3 text-foreground-secondary font-medium">
              {{ t("gateways.monitoring.time") }}
            </th>
            <th class="text-right px-4 py-3 text-foreground-secondary font-medium">
              {{ t("gateways.monitoring.cpu") }}
            </th>
            <th class="text-right px-4 py-3 text-foreground-secondary font-medium">
              {{ t("gateways.monitoring.memory") }}
            </th>
            <th class="text-right px-4 py-3 text-foreground-secondary font-medium">
              {{ t("gateways.monitoring.disk") }}
            </th>
            <th class="text-right px-4 py-3 text-foreground-secondary font-medium">
              {{ t("gateways.activeMounts") }}
            </th>
            <th class="text-right px-4 py-3 text-foreground-secondary font-medium">
              {{ t("gateways.monitoring.processCount") }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(data, index) in heartbeats.slice(-10).reverse()"
            :key="index"
            class="border-b border-border last:border-0"
          >
            <td class="px-4 py-2.5 text-foreground-secondary">
              {{ formatDate(data.timestamp) }}
            </td>
            <td class="px-4 py-2.5 text-right text-foreground">
              {{ data.cpu_usage?.toFixed(1) || "-" }}%
            </td>
            <td class="px-4 py-2.5 text-right text-foreground">
              {{ data.memory_usage?.toFixed(1) || "-" }}%
            </td>
            <td class="px-4 py-2.5 text-right text-foreground">
              {{ data.disk_usage?.toFixed(1) || "-" }}%
            </td>
            <td class="px-4 py-2.5 text-right text-foreground">
              {{ data.active_mounts || 0 }}
            </td>
            <td class="px-4 py-2.5 text-right text-foreground">
              {{ data.process_count || "-" }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
