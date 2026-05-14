<script setup lang="ts">
defineProps<{
  steps: string[];
  current: number;
}>();
</script>

<template>
  <div class="flex items-center gap-2 overflow-x-auto py-1">
    <template v-for="(step, index) in steps" :key="step">
      <div class="flex items-center gap-2 shrink-0">
        <div
          :class="[
            'w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold border',
            current > index + 1
              ? 'bg-emerald-600 border-emerald-600 text-white'
              : current === index + 1
                ? 'bg-primary border-primary text-primary-foreground'
                : 'bg-background-secondary border-border text-foreground-secondary',
          ]"
        >
          {{ index + 1 }}
        </div>
        <span
          :class="[
            'text-xs font-medium whitespace-nowrap',
            current === index + 1 ? 'text-foreground' : 'text-foreground-secondary',
          ]"
        >
          {{ step }}
        </span>
      </div>
      <div
        v-if="index < steps.length - 1"
        class="h-px w-8 shrink-0 bg-border"
      />
    </template>
  </div>
</template>
