<script setup lang="ts">
import { computed } from "vue";
import AppleIcon from "@iconify-vue/uiw/apple";
import LinuxIcon from "@iconify-vue/uiw/linux";
import WindowsIcon from "@iconify-vue/uiw/windows";
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

const sizeClass = computed(() => {
  return {
    sm: "h-3.5 w-3.5",
    md: "h-5 w-5",
    lg: "h-6 w-6",
  }[props.size];
});
</script>

<template>
  <WindowsIcon
    v-if="normalizedOs === 'windows'"
    :class="sizeClass"
    aria-hidden="true"
  />
  <AppleIcon
    v-else-if="normalizedOs === 'macos'"
    :class="sizeClass"
    aria-hidden="true"
  />
  <LinuxIcon
    v-else-if="normalizedOs === 'linux'"
    :class="sizeClass"
    aria-hidden="true"
  />
  <ServerIcon v-else :class="sizeClass" aria-hidden="true" />
</template>
