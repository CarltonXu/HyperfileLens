<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  CpuChipIcon,
  CircleStackIcon,
  ChatBubbleLeftRightIcon,
} from "@heroicons/vue/24/outline";

interface Gateway {
  id: string;
  name: string;
  description: string;
  hostname: string;
  internal_ip: string;
  os_version: string;
  version: string;
  kopia_version: string;
  cpu_cores: number;
  memory_total: number;
  disk_total: number;
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_bytes_sent?: number;
  network_bytes_recv?: number;
  heartbeat_interval?: number;
  uptime_seconds?: number;
  metadata?: Record<string, any>;
  active_mounts: number;
  max_concurrent_mounts: number;
  mount_base_path: string;
  ai_enabled: boolean;
  indexer_status: string;
  last_index_time: string;
  last_heartbeat: string;
  created_at: string;
  registered_at: string;
  tags: Record<string, string>;
  labels: string[];
}

defineProps<{
  gateway: Gateway;
}>();

const { t } = useI18n();

function formatBytes(bytes: number): string {
  if (!bytes) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

function formatDate(dateStr: string): string {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleString();
}

function formatUptime(seconds?: number | null): string {
  if (!seconds) return "-";
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function usageBarColor(value?: number | null): string {
  if (value === null || value === undefined) return "bg-slate-300";
  if (value > 80) return "bg-red-500";
  if (value > 60) return "bg-amber-500";
  return "bg-emerald-500";
}

function usageWidth(value?: number | null): string {
  if (value === null || value === undefined) return "0%";
  return `${Math.min(Math.max(value, 0), 100)}%`;
}
</script>

<template>
  <div class="space-y-6">
    <!-- Info Grid -->
    <div class="grid grid-cols-2 gap-4">
      <div class="bg-background-secondary rounded-lg p-4">
        <p class="text-sm text-foreground-secondary">
          {{ t("gateways.hostname") }}
        </p>
        <p class="text-base font-medium text-foreground mt-1">
          {{ gateway.hostname || "-" }}
        </p>
      </div>
      <div class="bg-background-secondary rounded-lg p-4">
        <p class="text-sm text-foreground-secondary">
          {{ t("gateways.internalIp") }}
        </p>
        <p class="text-base font-medium text-foreground mt-1">
          {{ gateway.internal_ip || "-" }}
        </p>
      </div>
      <div class="bg-background-secondary rounded-lg p-4">
        <p class="text-sm text-foreground-secondary">
          {{ t("gateways.osVersion") }}
        </p>
        <p class="text-base font-medium text-foreground mt-1">
          {{ gateway.os_version || "Ubuntu 22.04" }}
        </p>
      </div>
      <div class="bg-background-secondary rounded-lg p-4">
        <p class="text-sm text-foreground-secondary">
          {{ t("gateways.kopiaVersion") }}
        </p>
        <p class="text-base font-medium text-foreground mt-1">
          {{ gateway.kopia_version || "-" }}
        </p>
      </div>
      <div class="bg-background-secondary rounded-lg p-4">
        <p class="text-sm text-foreground-secondary">
          {{ t("gateways.version") }}
        </p>
        <p class="text-base font-medium text-foreground mt-1">
          {{ gateway.version || "-" }}
        </p>
      </div>
      <div class="bg-background-secondary rounded-lg p-4">
        <p class="text-sm text-foreground-secondary">
          {{ t("gateways.description") }}
        </p>
        <p class="text-base font-medium text-foreground mt-1">
          {{ gateway.description || "-" }}
        </p>
      </div>
    </div>

    <!-- Resources -->
    <div>
      <h3 class="text-sm font-semibold text-foreground mb-3">
        {{ t("gateways.resources") }}
      </h3>
      <div class="grid grid-cols-3 gap-4">
        <div class="bg-background-secondary rounded-lg p-4">
          <div class="flex items-center gap-2 text-foreground-secondary mb-1">
            <CpuChipIcon class="w-4 h-4" />
            <span class="text-sm">{{ t("gateways.cpu") }}</span>
          </div>
          <p class="text-lg font-semibold text-foreground">
            {{ gateway.cpu_cores || "-" }}
            {{ t("gateways.cores") }}
          </p>
          <p v-if="gateway.cpu_usage" class="text-sm text-foreground-secondary">
            {{ gateway.cpu_usage }}% {{ t("gateways.used") }}
          </p>
        </div>
        <div class="bg-background-secondary rounded-lg p-4">
          <div class="flex items-center gap-2 text-foreground-secondary mb-1">
            <CircleStackIcon class="w-4 h-4" />
            <span class="text-sm">{{ t("gateways.memory") }}</span>
          </div>
          <p class="text-lg font-semibold text-foreground">
            {{ gateway.memory_total ? formatBytes(gateway.memory_total) : "-" }}
          </p>
          <p
            v-if="
              gateway.memory_usage !== null &&
              gateway.memory_usage !== undefined
            "
            class="text-sm text-foreground-secondary"
          >
            {{ gateway.memory_usage.toFixed(1) }}% {{ t("gateways.used") }}
          </p>
          <div class="h-2 bg-slate-200 rounded-full overflow-hidden mt-2">
            <div
              class="h-full rounded-full transition-all"
              :class="usageBarColor(gateway.memory_usage)"
              :style="{ width: usageWidth(gateway.memory_usage) }"
            />
          </div>
        </div>
        <div class="bg-background-secondary rounded-lg p-4">
          <div class="flex items-center gap-2 text-foreground-secondary mb-1">
            <CircleStackIcon class="w-4 h-4" />
            <span class="text-sm">{{ t("gateways.disk") }}</span>
          </div>
          <p class="text-lg font-semibold text-foreground">
            {{ gateway.disk_total ? formatBytes(gateway.disk_total) : "-" }}
          </p>
          <p
            v-if="
              gateway.disk_usage !== null && gateway.disk_usage !== undefined
            "
            class="text-sm text-foreground-secondary"
          >
            {{ gateway.disk_usage.toFixed(1) }}% {{ t("gateways.used") }}
          </p>
          <div class="h-2 bg-slate-200 rounded-full overflow-hidden mt-2">
            <div
              class="h-full rounded-full transition-all"
              :class="usageBarColor(gateway.disk_usage)"
              :style="{ width: usageWidth(gateway.disk_usage) }"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Runtime -->
    <div>
      <h3 class="text-sm font-semibold text-foreground mb-3">
        {{ t("gateways.runtimeInfo") }}
      </h3>
      <div class="grid grid-cols-3 gap-4">
        <div class="bg-background-secondary rounded-lg p-4">
          <p class="text-sm text-foreground-secondary">
            {{ t("gateways.monitoring.uptime") }}
          </p>
          <p class="text-base font-medium text-foreground mt-1">
            {{
              formatUptime(
                gateway.metadata?.metrics?.uptime || gateway.uptime_seconds,
              )
            }}
          </p>
        </div>
        <div class="bg-background-secondary rounded-lg p-4">
          <p class="text-sm text-foreground-secondary">
            {{ t("gateways.monitoring.networkRecv") }}
          </p>
          <p class="text-base font-medium text-foreground mt-1">
            {{ formatBytes(gateway.network_bytes_recv || 0) }}
          </p>
        </div>
        <div class="bg-background-secondary rounded-lg p-4">
          <p class="text-sm text-foreground-secondary">
            {{ t("gateways.monitoring.networkSent") }}
          </p>
          <p class="text-base font-medium text-foreground mt-1">
            {{ formatBytes(gateway.network_bytes_sent || 0) }}
          </p>
        </div>
      </div>
    </div>

    <!-- Mount Info -->
    <div>
      <h3 class="text-sm font-semibold text-foreground mb-3">
        {{ t("gateways.mountInfo") }}
      </h3>
      <div class="bg-background-secondary rounded-lg p-4 space-y-3">
        <div class="flex items-center justify-between">
          <span class="text-sm text-foreground-secondary">{{
            t("gateways.activeMounts")
          }}</span>
          <span class="font-medium text-foreground"
            >{{ gateway.active_mounts }} /
            {{ gateway.max_concurrent_mounts }}</span
          >
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-foreground-secondary">{{
            t("gateways.mountBasePath")
          }}</span>
          <span class="font-medium text-foreground">{{
            gateway.mount_base_path
          }}</span>
        </div>
      </div>
    </div>

    <!-- AI Insights Status -->
    <div v-if="gateway.ai_enabled">
      <h3 class="text-sm font-semibold text-foreground mb-3">
        {{ t("gateways.aiInsights") }}
      </h3>
      <div class="bg-violet-50 dark:bg-violet-900/20 rounded-lg p-4">
        <div
          class="flex items-center gap-2 text-violet-600 dark:text-violet-400 mb-2"
        >
          <ChatBubbleLeftRightIcon class="w-5 h-5" />
          <span class="font-medium">{{ t("gateways.aiEnabled") }}</span>
        </div>
        <div class="grid grid-cols-2 gap-4 mt-3">
          <div>
            <p class="text-xs text-foreground-secondary">
              {{ t("gateways.indexerStatus") }}
            </p>
            <p class="text-sm font-medium text-foreground">
              {{ gateway.indexer_status || "-" }}
            </p>
          </div>
          <div v-if="gateway.last_index_time">
            <p class="text-xs text-foreground-secondary">
              {{ t("gateways.lastIndexTime") }}
            </p>
            <p class="text-sm font-medium text-foreground">
              {{ formatDate(gateway.last_index_time) }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Labels -->
    <div v-if="gateway.labels && gateway.labels.length > 0">
      <h3 class="text-sm font-semibold text-foreground mb-3">
        {{ t("gateways.labels") }}
      </h3>
      <div class="flex flex-wrap gap-2">
        <span
          v-for="label in gateway.labels"
          :key="label"
          class="px-3 py-1 bg-background-tertiary text-foreground-secondary rounded-full text-sm"
        >
          {{ label }}
        </span>
      </div>
    </div>

    <!-- Timestamps -->
    <div class="text-sm text-foreground-secondary space-y-1">
      <p>
        {{ t("gateways.createdAt") }}:
        {{ formatDate(gateway.created_at) }}
      </p>
      <p v-if="gateway.registered_at">
        {{ t("gateways.registeredAt") }}:
        {{ formatDate(gateway.registered_at) }}
      </p>
      <p v-if="gateway.last_heartbeat">
        {{ t("gateways.lastHeartbeat") }}:
        {{ formatDate(gateway.last_heartbeat) }}
      </p>
    </div>
  </div>
</template>
