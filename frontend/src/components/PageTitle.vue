<script setup lang="ts">
import type { Component } from "vue";

defineProps<{
  title: string;
  subtitle?: string;
  icon: Component;
  iconClass?: string;
}>();
</script>

<template>
  <div class="flex min-w-0 items-start gap-3">
    <div
      :class="[
        'flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-background-secondary',
        iconClass || 'text-primary',
      ]"
    >
      <component :is="icon" class="h-5 w-5" />
    </div>
    <div class="min-w-0">
      <h1 class="text-2xl font-bold text-foreground">
        {{ title }}
      </h1>
      <p v-if="subtitle" class="mt-1 text-sm text-foreground-secondary">
        {{ subtitle }}
      </p>
    </div>
  </div>
</template>
