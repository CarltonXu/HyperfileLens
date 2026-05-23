<script setup lang="ts">
import { useI18n } from "vue-i18n";

defineProps<{
  interfaces: any[];
  formatBytes: (bytes?: number | null) => string;
}>();

const { t } = useI18n();
</script>

<template>
  <div v-if="interfaces.length > 0" class="mb-4 overflow-x-auto">
    <table class="w-full text-sm">
      <thead>
        <tr class="border-b border-border">
          <th class="text-left py-2 px-3 text-foreground-secondary font-medium">
            {{ t("gateways.monitoring.interface") }}
          </th>
          <th class="text-left py-2 px-3 text-foreground-secondary font-medium">
            {{ t("gateways.monitoring.ipAddress") }}
          </th>
          <th class="text-left py-2 px-3 text-foreground-secondary font-medium">
            {{ t("gateways.monitoring.macAddress") }}
          </th>
          <th class="text-right py-2 px-3 text-foreground-secondary font-medium">
            {{ t("gateways.monitoring.bytesIn") }}
          </th>
          <th class="text-right py-2 px-3 text-foreground-secondary font-medium">
            {{ t("gateways.monitoring.bytesOut") }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="item in interfaces"
          :key="item.name"
          class="border-b border-border last:border-0 hover:bg-hover"
        >
          <td class="py-2 px-3 font-medium text-foreground">
            <div class="flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-green-500"></span>
              {{ item.name }}
            </div>
          </td>
          <td class="py-2 px-3 text-foreground-secondary font-mono text-xs">
            {{ item.ip_address || item.ip_addresses?.[0] || "-" }}
          </td>
          <td class="py-2 px-3 text-foreground-secondary font-mono text-xs">
            {{ item.mac_address || item.mac || "-" }}
          </td>
          <td class="py-2 px-3 text-right text-foreground-secondary">
            {{ formatBytes(item.bytes_in) }}
          </td>
          <td class="py-2 px-3 text-right text-foreground-secondary">
            {{ formatBytes(item.bytes_out) }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
