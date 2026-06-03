<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  BeakerIcon,
  EyeIcon,
  PencilSquareIcon,
  PowerIcon,
  TrashIcon,
} from "@heroicons/vue/24/outline";
import ResizableSortableTh from "@/components/ResizableSortableTh.vue";
import type { NotificationChannel } from "@/types/alerts";

type NotificationChannelColumnKey =
  | "name"
  | "type"
  | "enabled"
  | "target"
  | "updated_at"
  | "actions";

type NotificationChannelColumn = {
  key: NotificationChannelColumnKey;
  label: string;
  min: number;
  max: number;
  sortable?: boolean;
  align?: "left" | "right" | "center";
};

const props = defineProps<{
  channels: NotificationChannel[];
  columns: NotificationChannelColumn[];
  table: any;
  channelIcons: Record<string, any>;
  channelColors: Record<string, string>;
  getChannelTarget: (channel: NotificationChannel) => string;
}>();

defineEmits<{
  test: [channel: NotificationChannel];
  toggle: [channel: NotificationChannel];
  details: [channel: NotificationChannel];
  edit: [channel: NotificationChannel];
  delete: [channel: NotificationChannel];
}>();

const { t } = useI18n();

function sortColumn(key: string) {
  props.table.toggleSort(key as NotificationChannelColumnKey);
}

function startResize(key: string, event: MouseEvent) {
  props.table.startResize(key as NotificationChannelColumnKey, event);
}

function resetColumnWidth(key: string) {
  props.table.resetColumnWidth(key as NotificationChannelColumnKey);
}
</script>

<template>
  <div
    class="relative min-h-0 flex-1 overflow-auto bg-card"
  >
      <table
        class="w-full table-fixed border-separate border-spacing-0 text-left text-sm"
        :style="{ minWidth: table.tableMinWidth.value }"
      >
        <colgroup>
          <col
            v-for="column in columns"
            :key="column.key"
            :style="table.columnStyle(column.key)"
          />
        </colgroup>
        <thead class="sticky top-0 z-30 bg-background-secondary shadow-sm">
          <tr>
            <ResizableSortableTh
              v-for="column in columns"
              :key="column.key"
              :column-key="column.key"
              :label="column.label"
              :style-value="table.columnStyle(column.key)"
              :sortable="column.sortable !== false"
              :active="table.sort.value.key === column.key"
              :align="column.align"
              :sort-icon="table.getSortIcon(column.key)"
              :resizing="table.resizingColumn.value === column.key"
              header-class="border-b border-border"
              @sort="sortColumn"
              @resize-start="startResize"
              @resize-reset="resetColumnWidth"
            />
          </tr>
        </thead>
        <tbody class="[&>tr>td]:border-b [&>tr>td]:border-border">
          <tr
            v-for="channel in channels"
            :key="channel.id"
            class="transition-colors hover:bg-hover"
          >
            <td class="px-4 py-4" :style="table.columnStyle('name')">
              <div class="flex items-center gap-2">
                <component
                  :is="channelIcons[channel.type]"
                  class="h-4 w-4 text-foreground-secondary"
                />
                <span class="font-medium text-foreground">{{
                  channel.name
                }}</span>
              </div>
            </td>
            <td class="px-4 py-4" :style="table.columnStyle('type')">
              <span
                class="inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium"
                :class="channelColors[channel.type]"
              >
                {{ t(`alertsCenter.values.${channel.type}`) }}
              </span>
            </td>
            <td class="px-4 py-4" :style="table.columnStyle('enabled')">
              <span
                :class="
                  channel.enabled
                    ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400'
                    : 'bg-zinc-100 text-zinc-700 dark:bg-zinc-500/10 dark:text-zinc-400'
                "
                class="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium"
              >
                <span
                  :class="[
                    'h-1.5 w-1.5 rounded-full',
                    channel.enabled ? 'bg-emerald-500' : 'bg-zinc-500',
                  ]"
                />
                {{
                  channel.enabled
                    ? t("alertsCenter.values.enabled")
                    : t("alertsCenter.values.disabled")
                }}
              </span>
            </td>
            <td
              class="max-w-[300px] truncate px-4 py-4 text-foreground-secondary"
              :style="table.columnStyle('target')"
            >
              {{ getChannelTarget(channel) }}
            </td>
            <td
              class="px-4 py-4 text-foreground-secondary"
              :style="table.columnStyle('updated_at')"
            >
              {{
                new Date(
                  channel.updated_at || channel.created_at,
                ).toLocaleString()
              }}
            </td>
            <td class="px-4 py-4" :style="table.columnStyle('actions')">
              <div class="flex justify-end gap-1">
                <button
                  class="rounded-lg p-2 text-foreground-secondary transition-colors hover:bg-hover hover:text-foreground"
                  :title="t('alertsCenter.common.test')"
                  @click="$emit('test', channel)"
                >
                  <BeakerIcon class="h-4 w-4" />
                </button>
                <button
                  class="rounded-lg p-2 text-foreground-secondary transition-colors hover:bg-hover hover:text-foreground"
                  :title="
                    channel.enabled
                      ? t('alertsCenter.common.disabled')
                      : t('alertsCenter.values.enabled')
                  "
                  @click="$emit('toggle', channel)"
                >
                  <PowerIcon
                    :class="[
                      'h-4 w-4',
                      channel.enabled
                        ? 'text-emerald-500'
                        : 'text-foreground-muted',
                    ]"
                  />
                </button>
                <button
                  class="rounded-lg p-2 text-foreground-secondary transition-colors hover:bg-hover hover:text-foreground"
                  :title="t('alertsCenter.common.viewDetails')"
                  @click="$emit('details', channel)"
                >
                  <EyeIcon class="h-4 w-4" />
                </button>
                <button
                  class="rounded-lg p-2 text-foreground-secondary transition-colors hover:bg-hover hover:text-foreground"
                  :title="$t('common.edit')"
                  @click="$emit('edit', channel)"
                >
                  <PencilSquareIcon class="h-4 w-4" />
                </button>
                <button
                  class="rounded-lg p-2 text-red-500 transition-colors hover:bg-red-50 dark:hover:bg-red-500/10"
                  :title="$t('common.delete')"
                  @click="$emit('delete', channel)"
                >
                  <TrashIcon class="h-4 w-4" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
  </div>
</template>
