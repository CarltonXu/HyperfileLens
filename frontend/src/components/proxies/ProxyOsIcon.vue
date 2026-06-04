<script setup lang="ts">
import { computed } from "vue";
import { Icon } from "@iconify/vue";
import linuxTuxIcon from "@iconify-icons/logos/linux-tux";
import windowsIcon from "@iconify-icons/logos/microsoft-windows";
import appleIcon from "@iconify-icons/simple-icons/apple";
import { ServerIcon } from "@heroicons/vue/24/outline";

const props = withDefaults(
  defineProps<{
    os?: string | null;
    targetOs?: string | null;
    size?: "sm" | "md" | "lg";
  }>(),
  {
    os: null,
    targetOs: null,
    size: "md",
  },
);

const normalizedOs = computed(() => {
  const value = `${props.os || props.targetOs || ""}`.toLowerCase();
  if (value.includes("windows") || value.includes("win32")) return "windows";
  if (
    value.includes("macos") ||
    value.includes("darwin") ||
    value.includes("os x")
  ) {
    return "macos";
  }
  if (
    value.includes("linux") ||
    value.includes("ubuntu") ||
    value.includes("debian") ||
    value.includes("centos") ||
    value.includes("rhel") ||
    value.includes("rocky") ||
    value.includes("almalinux")
  ) {
    return "linux";
  }
  return "unknown";
});

const osIcon = computed(() => {
  if (normalizedOs.value === "windows") return windowsIcon;
  if (normalizedOs.value === "macos") return appleIcon;
  if (normalizedOs.value === "linux") return linuxTuxIcon;
  return null;
});

const sizeClass = computed(() => {
  return {
    sm: "h-4 w-4",
    md: "h-6 w-6",
    lg: "h-8 w-8",
  }[props.size];
});
</script>

<template>
  <Icon v-if="osIcon" :icon="osIcon" :class="sizeClass" aria-hidden="true" />
  <ServerIcon v-else :class="sizeClass" aria-hidden="true" />
</template>
