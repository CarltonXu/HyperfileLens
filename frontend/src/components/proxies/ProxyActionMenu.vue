<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  ArrowPathIcon,
  InformationCircleIcon,
  PauseIcon,
  PencilIcon,
  PlayIcon,
  TrashIcon,
} from "@heroicons/vue/24/outline";
import type { ProxyNode } from "@/types/proxy";

defineProps<{
  proxy: ProxyNode;
  open: boolean;
  menuStyle: Record<string, string>;
}>();

defineEmits<{
  close: [];
  detail: [proxy: ProxyNode];
  edit: [proxy: ProxyNode];
  regenerateToken: [proxy: ProxyNode];
  updateStatus: [proxy: ProxyNode, status: string];
  delete: [proxy: ProxyNode];
}>();

const { t } = useI18n();
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed popover-surface rounded-lg shadow-lg border border-border py-1 z-[9999]"
      :style="menuStyle"
    >
      <button
        class="w-full px-4 py-2 text-left text-sm text-foreground hover:bg-hover flex items-center gap-2"
        @click="
          $emit('detail', proxy);
          $emit('close');
        "
      >
        <InformationCircleIcon class="w-4 h-4" />
        {{ t("proxies.actions.viewDetails") }}
      </button>
      <button
        class="w-full px-4 py-2 text-left text-sm text-foreground hover:bg-hover flex items-center gap-2"
        @click="
          $emit('edit', proxy);
          $emit('close');
        "
      >
        <PencilIcon class="w-4 h-4" />
        {{ t("proxies.actions.edit") }}
      </button>
      <button
        class="w-full px-4 py-2 text-left text-sm text-foreground hover:bg-hover flex items-center gap-2"
        @click="
          $emit('regenerateToken', proxy);
          $emit('close');
        "
      >
        <ArrowPathIcon class="w-4 h-4" />
        {{ t("proxies.actions.regenerateToken") }}
      </button>
      <hr class="my-1 border-border" />
      <button
        v-if="proxy.status === 'online'"
        class="w-full px-4 py-2 text-left text-sm text-amber-600 dark:text-amber-400 hover:bg-amber-50 flex items-center gap-2"
        @click="
          $emit('updateStatus', proxy, 'maintenance');
          $emit('close');
        "
      >
        <PauseIcon class="w-4 h-4" />
        {{ t("proxies.actions.setMaintenance") }}
      </button>
      <button
        v-else-if="proxy.status === 'maintenance'"
        class="w-full px-4 py-2 text-left text-sm text-emerald-600 dark:text-emerald-400 hover:bg-emerald-50 flex items-center gap-2"
        @click="
          $emit('updateStatus', proxy, 'online');
          $emit('close');
        "
      >
        <PlayIcon class="w-4 h-4" />
        {{ t("proxies.actions.activate") }}
      </button>
      <hr class="my-1 border-border" />
      <button
        class="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
        @click="
          $emit('delete', proxy);
          $emit('close');
        "
      >
        <TrashIcon class="w-4 h-4" />
        {{ t("proxies.actions.delete") }}
      </button>
    </div>
  </Teleport>
</template>
