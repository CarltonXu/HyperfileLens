<script setup lang="ts">
import { CheckCircleIcon } from "@heroicons/vue/24/outline";

defineProps<{
  steps: Array<{
    key: string;
    label: string;
    description: string;
  }>;
  currentStep: number;
}>();
</script>

<template>
  <div class="px-6 py-4 border-b border-border bg-background-secondary/30">
    <div class="grid grid-cols-5 gap-0">
      <div
        v-for="(step, index) in steps"
        :key="step.key"
        class="relative flex flex-col items-center text-center"
      >
        <div
          v-if="index > 0"
          :class="[
            'absolute top-4 right-1/2 h-0.5 w-full -z-0',
            index <= currentStep ? 'bg-emerald-500' : 'bg-border',
          ]"
        />
        <div
          :class="[
            'relative z-10 w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold border-2 bg-card',
            index < currentStep
              ? 'border-emerald-500 bg-emerald-500 text-white'
              : index === currentStep
                ? 'border-emerald-500 text-emerald-600'
                : 'border-border text-foreground-secondary',
          ]"
        >
          <CheckCircleIcon v-if="index < currentStep" class="w-4 h-4" />
          <span v-else>{{ index + 1 }}</span>
        </div>
        <p
          :class="[
            'mt-2 text-xs font-medium',
            index === currentStep ? 'text-foreground' : 'text-foreground-secondary',
          ]"
        >
          {{ step.label }}
        </p>
      </div>
    </div>
  </div>
</template>
