<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  ArrowPathIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  PauseIcon,
  PencilIcon,
  PlayIcon,
  TrashIcon,
} from "@heroicons/vue/24/outline";

interface Gateway {
  id: string;
  name: string;
  status: string;
  [key: string]: any;
}

defineProps<{
  gateway: Gateway;
  open: boolean;
  menuStyle: Record<string, string>;
}>();

defineEmits<{
  close: [];
  detail: [gateway: Gateway];
  edit: [gateway: Gateway];
  regenerateToken: [gateway: Gateway];
  updateStatus: [gateway: Gateway, status: string];
  installInfo: [gateway: Gateway];
  delete: [gateway: Gateway];
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
          $emit('detail', gateway);
          $emit('close');
        "
      >
        <InformationCircleIcon class="w-4 h-4" />
        {{ t("gateways.actions.viewDetails") }}
      </button>
      <button
        v-if="!gateway.is_online"
        class="w-full px-4 py-2 text-left text-sm text-amber-600 dark:text-amber-400 hover:bg-amber-50 flex items-center gap-2"
        @click="
          $emit('installInfo', gateway);
          $emit('close');
        "
      >
        <ExclamationTriangleIcon class="w-4 h-4" />
        {{ t("gateways.actions.viewInstall") }}
      </button>
      <button
        class="w-full px-4 py-2 text-left text-sm text-foreground hover:bg-hover flex items-center gap-2"
        @click="
          $emit('edit', gateway);
          $emit('close');
        "
      >
        <PencilIcon class="w-4 h-4" />
        {{ t("gateways.actions.edit") }}
      </button>
      <button
        class="w-full px-4 py-2 text-left text-sm text-foreground hover:bg-hover flex items-center gap-2"
        @click="
          $emit('regenerateToken', gateway);
          $emit('close');
        "
      >
        <ArrowPathIcon class="w-4 h-4" />
        {{ t("gateways.actions.regenerateToken") }}
      </button>
      <hr class="my-1 border-border" />
      <button
        v-if="gateway.status === 'active'"
        class="w-full px-4 py-2 text-left text-sm text-amber-600 dark:text-amber-400 hover:bg-amber-50 flex items-center gap-2"
        @click="
          $emit('updateStatus', gateway, 'maintenance');
          $emit('close');
        "
      >
        <PauseIcon class="w-4 h-4" />
        {{ t("gateways.actions.setMaintenance") }}
      </button>
      <button
        v-else-if="gateway.status === 'maintenance'"
        class="w-full px-4 py-2 text-left text-sm text-emerald-600 dark:text-emerald-400 hover:bg-emerald-50 flex items-center gap-2"
        @click="
          $emit('updateStatus', gateway, 'active');
          $emit('close');
        "
      >
        <PlayIcon class="w-4 h-4" />
        {{ t("gateways.actions.activate") }}
      </button>
      <hr class="my-1 border-border" />
      <button
        class="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
        @click="
          $emit('delete', gateway);
          $emit('close');
        "
      >
        <TrashIcon class="w-4 h-4" />
        {{ t("gateways.actions.delete") }}
      </button>
    </div>
  </Teleport>
</template>
