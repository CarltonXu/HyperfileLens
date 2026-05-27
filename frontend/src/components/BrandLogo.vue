<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    variant?: "mark" | "full";
    size?: "sm" | "md" | "lg";
  }>(),
  {
    variant: "full",
    size: "md",
  },
);

const markSizeClass = computed(() => {
  return {
    sm: "h-8 w-8",
    md: "h-10 w-10",
    lg: "h-12 w-12",
  }[props.size];
});

const textSizeClass = computed(() => {
  return {
    sm: "text-base",
    md: "text-lg",
    lg: "text-xl",
  }[props.size];
});
</script>

<template>
  <span class="inline-flex items-center gap-2.5 align-middle">
    <span
      :class="[
        'inline-flex shrink-0 items-center justify-center rounded-xl shadow-sm',
        markSizeClass,
      ]"
      aria-hidden="true"
    >
      <svg
        class="h-full w-full"
        viewBox="0 0 64 64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <rect width="64" height="64" rx="14" fill="url(#brand-bg)" />
        <path
          d="M48 12.5L49.35 16.15L53 17.5L49.35 18.85L48 22.5L46.65 18.85L43 17.5L46.65 16.15L48 12.5Z"
          fill="#F5D0FE"
          fill-opacity="0.9"
        />
        <path
          d="M39.5 13.5L43.5 16.5M52 24L49.25 20.25"
          stroke="#DDD6FE"
          stroke-width="1.6"
          stroke-linecap="round"
          stroke-opacity="0.72"
        />
        <circle cx="38.5" cy="13" r="2" fill="#DDD6FE" fill-opacity="0.78" />
        <circle cx="53" cy="25.5" r="2" fill="#C4B5FD" fill-opacity="0.78" />
        <path
          d="M16 21.5C16 18.4624 18.4624 16 21.5 16H39.5C42.5376 16 45 18.4624 45 21.5V42.5C45 45.5376 42.5376 48 39.5 48H21.5C18.4624 48 16 45.5376 16 42.5V21.5Z"
          fill="white"
          fill-opacity="0.2"
        />
        <path
          d="M21 23H38M21 31H34M21 39H30"
          stroke="white"
          stroke-opacity="0.94"
          stroke-width="3"
          stroke-linecap="round"
        />
        <circle cx="40" cy="39" r="9" stroke="#C4B5FD" stroke-width="4" />
        <path
          d="M46.5 45.5L52 51"
          stroke="#A78BFA"
          stroke-width="4"
          stroke-linecap="round"
        />
        <path
          d="M38.25 33.5L41 38.75L35.5 38.25"
          stroke="#F0ABFC"
          stroke-width="2.8"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
        <defs>
          <linearGradient
            id="brand-bg"
            x1="8"
            y1="7"
            x2="56"
            y2="57"
            gradientUnits="userSpaceOnUse"
          >
            <stop stop-color="#111827" />
            <stop offset="0.46" stop-color="#3730A3" />
            <stop offset="1" stop-color="#7C3AED" />
          </linearGradient>
        </defs>
      </svg>
    </span>
    <span
      v-if="variant === 'full'"
      :class="['font-bold leading-none text-foreground', textSizeClass]"
    >
      <span>Hyper</span>
      <span
        class="bg-gradient-to-r from-violet-500 via-fuchsia-500 to-indigo-500 bg-clip-text text-transparent"
      >
        FileLens
      </span>
    </span>
  </span>
</template>
