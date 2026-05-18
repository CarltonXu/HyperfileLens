<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import {
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  XMarkIcon,
} from "@heroicons/vue/24/solid";

interface Toast {
  id: string;
  type: "success" | "error" | "warning" | "info";
  title: string;
  message?: string;
  duration?: number;
}

const props = defineProps<Toast>();
const emit = defineEmits<{
  close: [id: string];
}>();

const progress = ref(100);
const isPaused = ref(false);
const isLeaving = ref(false);
let animationFrame: number | null = null;
let timeoutId: ReturnType<typeof setTimeout> | null = null;
let startedAt = 0;
let pausedAt = 0;
let remainingMs = 0;

// Icon based on type
const iconComponent = computed(() => {
  switch (props.type) {
    case "success":
      return CheckCircleIcon;
    case "error":
      return XCircleIcon;
    case "warning":
      return ExclamationTriangleIcon;
    case "info":
      return InformationCircleIcon;
  }
});

// Modern color scheme with gradients
const styles = computed(() => {
  const styleMap = {
    success: {
      bg: "bg-gradient-to-r from-emerald-50 to-green-50 dark:from-emerald-950/90 dark:to-green-950/90",
      border: "border-l-4 border-emerald-500",
      icon: "text-emerald-500",
      iconBg: "bg-emerald-100 dark:bg-emerald-900/50",
      title: "text-emerald-900 dark:text-emerald-100",
      message: "text-emerald-700 dark:text-emerald-300",
      progress: "bg-gradient-to-r from-emerald-400 to-green-500",
      glow: "shadow-emerald-500/20 dark:shadow-emerald-500/30",
    },
    error: {
      bg: "bg-gradient-to-r from-red-50 to-rose-50 dark:from-red-950/90 dark:to-rose-950/90",
      border: "border-l-4 border-red-500",
      icon: "text-red-500",
      iconBg: "bg-red-100 dark:bg-red-900/50",
      title: "text-red-900 dark:text-red-100",
      message: "text-red-700 dark:text-red-300",
      progress: "bg-gradient-to-r from-red-400 to-rose-500",
      glow: "shadow-red-500/20 dark:shadow-red-500/30",
    },
    warning: {
      bg: "bg-gradient-to-r from-amber-50 to-yellow-50 dark:from-amber-950/90 dark:to-yellow-950/90",
      border: "border-l-4 border-amber-500",
      icon: "text-amber-500",
      iconBg: "bg-amber-100 dark:bg-amber-900/50",
      title: "text-amber-900 dark:text-amber-100",
      message: "text-amber-700 dark:text-amber-300",
      progress: "bg-gradient-to-r from-amber-400 to-yellow-500",
      glow: "shadow-amber-500/20 dark:shadow-amber-500/30",
    },
    info: {
      bg: "bg-gradient-to-r from-blue-50 to-sky-50 dark:from-blue-950/90 dark:to-sky-950/90",
      border: "border-l-4 border-blue-500",
      icon: "text-blue-500",
      iconBg: "bg-blue-100 dark:bg-blue-900/50",
      title: "text-blue-900 dark:text-blue-100",
      message: "text-blue-700 dark:text-blue-300",
      progress: "bg-gradient-to-r from-blue-400 to-sky-500",
      glow: "shadow-blue-500/20 dark:shadow-blue-500/30",
    },
  };
  return styleMap[props.type];
});

const stopTimer = () => {
  if (timeoutId) {
    clearTimeout(timeoutId);
    timeoutId = null;
  }
};

const stopProgress = () => {
  if (animationFrame) {
    cancelAnimationFrame(animationFrame);
    animationFrame = null;
  }
};

const startAutoClose = () => {
  if (!props.duration || props.duration <= 0) return;
  remainingMs = remainingMs || props.duration;
  startedAt = Date.now();
  stopTimer();
  timeoutId = setTimeout(close, remainingMs);
};

// Progress bar animation
const startProgress = () => {
  if (!props.duration || props.duration <= 0) return;
  const duration = props.duration;
  stopProgress();
  const updateProgress = () => {
    if (isPaused.value) {
      animationFrame = requestAnimationFrame(updateProgress);
      return;
    }

    const elapsed = Date.now() - startedAt;
    const currentRemaining = Math.max(0, remainingMs - elapsed);
    progress.value = (currentRemaining / duration) * 100;

    if (currentRemaining > 0) {
      animationFrame = requestAnimationFrame(updateProgress);
    }
  };

  animationFrame = requestAnimationFrame(updateProgress);
};

onMounted(() => {
  remainingMs = props.duration || 0;
  startAutoClose();
  startProgress();
});

onUnmounted(() => {
  stopProgress();
  stopTimer();
});

const close = () => {
  stopProgress();
  stopTimer();
  isLeaving.value = true;
  // Small delay for animation
  timeoutId = setTimeout(() => {
    emit("close", props.id);
  }, 200);
};

const pauseProgress = () => {
  if (!props.duration || props.duration <= 0 || isPaused.value) return;
  isPaused.value = true;
  pausedAt = Date.now();
  remainingMs = Math.max(0, remainingMs - (pausedAt - startedAt));
  stopTimer();
};

const resumeProgress = () => {
  if (!props.duration || props.duration <= 0 || !isPaused.value) return;
  isPaused.value = false;
  startAutoClose();
};
</script>

<template>
  <div
    :class="[
      'relative overflow-hidden rounded-xl shadow-lg backdrop-blur-sm',
      styles.bg,
      styles.border,
      styles.glow,
      'min-w-[340px] max-w-[560px]',
      'pointer-events-auto',
      'transform transition-all duration-200 ease-out',
      isLeaving
        ? 'opacity-0 translate-x-4 scale-95'
        : 'opacity-100 translate-x-0 scale-100',
    ]"
    @mouseenter="pauseProgress"
    @mouseleave="resumeProgress">
    <div class="flex items-start p-4 gap-3">
      <!-- Icon with background -->
      <div :class="['flex-shrink-0 p-1.5 rounded-lg', styles.iconBg]">
        <component :is="iconComponent" :class="['h-5 w-5', styles.icon]" />
      </div>

      <!-- Content -->
      <div class="flex-1 min-w-0">
        <p :class="['text-sm font-semibold leading-5 break-words', styles.title]">
          {{ title }}
        </p>
        <p
          v-if="message"
          :class="[
            'mt-1 max-h-40 overflow-y-auto whitespace-pre-wrap break-words text-sm leading-5 opacity-90',
            styles.message,
          ]">
          {{ message }}
        </p>
      </div>

      <!-- Close button -->
      <button
        type="button"
        :class="[
          'flex-shrink-0 p-1 rounded-lg transition-colors',
          'text-gray-400 hover:text-gray-600 hover:bg-gray-100',
          'dark:text-gray-500 dark:hover:text-gray-300 dark:hover:bg-gray-800',
          'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-400',
        ]"
        @click="close">
        <span class="sr-only">Close</span>
        <XMarkIcon class="h-4 w-4" />
      </button>
    </div>

    <!-- Progress bar -->
    <div
      v-if="duration && duration > 0"
      class="absolute bottom-0 left-0 right-0 h-1 bg-black/5 dark:bg-white/10">
      <div
        :class="[
          'h-full transition-[width] duration-100 ease-linear rounded-r-full',
          styles.progress,
        ]"
        :style="{ width: `${progress}%` }" />
    </div>
  </div>
</template>
