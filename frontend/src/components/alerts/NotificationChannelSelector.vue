<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import { ChevronDownIcon } from "@heroicons/vue/24/outline";

const model = defineModel<string[]>({ required: true });
const props = defineProps<{
  channels: Array<{ id: string; name: string; type: string; enabled: boolean }>;
}>();
const { t } = useI18n();
const open = ref(false);

const selectedChannels = computed(() => {
  const selected = new Set(model.value);
  return props.channels.filter((channel) => selected.has(channel.id));
});

const selectedLabel = computed(() => {
  if (!selectedChannels.value.length)
    return t("alertsCenter.common.noChannelSelected");
  return selectedChannels.value.map((channel) => channel.name).join(", ");
});

function toggle(id: string) {
  model.value = model.value.includes(id)
    ? model.value.filter((item) => item !== id)
    : [...model.value, id];
}
</script>

<template>
  <div class="relative">
    <button
      type="button"
      class="flex h-10 w-full items-center justify-between gap-2 rounded-lg border border-border bg-background px-3 text-left text-sm text-foreground outline-none transition-colors hover:bg-hover focus:border-primary focus:ring-2 focus:ring-primary/20"
      @click="open = !open">
      <span
        class="min-w-0 flex-1 truncate"
        :class="
          selectedChannels.length
            ? 'text-foreground'
            : 'text-foreground-secondary'
        ">
        {{ selectedLabel }}
      </span>
      <span
        v-if="selectedChannels.length"
        class="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
        {{ selectedChannels.length }}
      </span>
      <ChevronDownIcon
        class="h-4 w-4 shrink-0 text-foreground-secondary transition-transform"
        :class="open && 'rotate-180'" />
    </button>

    <div
      v-if="open"
      class="absolute left-0 right-0 z-50 mt-2 max-h-72 overflow-auto rounded-lg border border-border bg-background-secondary p-2 shadow-xl">
      <div
        v-if="channels.length === 0"
        class="px-3 py-6 text-center text-sm text-foreground-secondary">
        {{ t("common.noData") }}
      </div>
      <button
        v-for="channel in channels"
        :key="channel.id"
        type="button"
        class="flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm text-foreground hover:bg-hover"
        @click="toggle(channel.id)">
        <input
          type="checkbox"
          class="pointer-events-none rounded border-border text-primary focus:ring-primary"
          :checked="model.includes(channel.id)"
          tabindex="-1" />
        <span class="min-w-0 flex-1">
          <span class="block truncate font-medium">{{ channel.name }}</span>
          <span class="block truncate text-xs text-foreground-secondary">{{
            t(`alertsCenter.values.${channel.type}`)
          }}</span>
        </span>
        <span class="shrink-0 text-xs text-foreground-secondary">
          {{
            channel.enabled
              ? t("alertsCenter.values.enabled")
              : t("alertsCenter.values.disabled")
          }}
        </span>
      </button>
    </div>
  </div>
</template>
