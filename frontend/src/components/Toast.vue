<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  XMarkIcon
} from '@heroicons/vue/24/outline'

interface Toast {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message?: string
  duration?: number
}

const props = defineProps<Toast>()
const emit = defineEmits<{
  close: [id: string]
}>()

const progress = ref(100)
const isPaused = ref(false)

// Icon and style based on type
const iconComponent = computed(() => {
  switch (props.type) {
    case 'success': return CheckCircleIcon
    case 'error': return XCircleIcon
    case 'warning': return ExclamationTriangleIcon
    case 'info': return InformationCircleIcon
  }
})

const styles = computed(() => {
  const styleMap = {
    success: {
      bg: 'bg-white dark:bg-gray-800',
      border: 'border-l-4 border-success-500',
      icon: 'text-success-500',
      progress: 'bg-success-500',
      shadow: 'shadow-success-100 dark:shadow-success-900/20'
    },
    error: {
      bg: 'bg-white dark:bg-gray-800',
      border: 'border-l-4 border-danger-500',
      icon: 'text-danger-500',
      progress: 'bg-danger-500',
      shadow: 'shadow-danger-100 dark:shadow-danger-900/20'
    },
    warning: {
      bg: 'bg-white dark:bg-gray-800',
      border: 'border-l-4 border-warning-500',
      icon: 'text-warning-500',
      progress: 'bg-warning-500',
      shadow: 'shadow-warning-100 dark:shadow-warning-900/20'
    },
    info: {
      bg: 'bg-white dark:bg-gray-800',
      border: 'border-l-4 border-primary-500',
      icon: 'text-primary-500',
      progress: 'bg-primary-500',
      shadow: 'shadow-primary-100 dark:shadow-primary-900/20'
    }
  }
  return styleMap[props.type]
})

// Progress bar animation
onMounted(() => {
  if (props.duration && props.duration > 0) {
    const startTime = Date.now()
    const duration = props.duration

    const updateProgress = () => {
      if (isPaused.value) return

      const elapsed = Date.now() - startTime
      const remaining = Math.max(0, 100 - (elapsed / duration) * 100)
      progress.value = remaining

      if (remaining > 0) {
        requestAnimationFrame(updateProgress)
      }
    }

    requestAnimationFrame(updateProgress)
  }
})

const close = () => {
  emit('close', props.id)
}

const pauseProgress = () => {
  isPaused.value = true
}

const resumeProgress = () => {
  isPaused.value = false
}
</script>

<template>
  <div
    :class="[
      'relative overflow-hidden rounded-lg shadow-lg',
      styles.bg,
      styles.border,
      styles.shadow,
      'min-w-[320px] max-w-[420px]',
      'pointer-events-auto'
    ]"
    @mouseenter="pauseProgress"
    @mouseleave="resumeProgress"
  >
    <div class="flex items-start p-4">
      <!-- Icon -->
      <div class="flex-shrink-0">
        <component
          :is="iconComponent"
          :class="['h-6 w-6', styles.icon]"
        />
      </div>

      <!-- Content -->
      <div class="ml-3 flex-1">
        <p class="text-sm font-semibold text-gray-900 dark:text-white">
          {{ title }}
        </p>
        <p v-if="message" class="mt-1 text-sm text-gray-500 dark:text-gray-400">
          {{ message }}
        </p>
      </div>

      <!-- Close button -->
      <button
        type="button"
        class="ml-4 flex-shrink-0 inline-flex rounded-md text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
        @click="close"
      >
        <span class="sr-only">Close</span>
        <XMarkIcon class="h-5 w-5" />
      </button>
    </div>

    <!-- Progress bar -->
    <div
      v-if="duration && duration > 0"
      class="absolute bottom-0 left-0 right-0 h-1 bg-gray-100 dark:bg-gray-700"
    >
      <div
        :class="['h-full transition-[width] duration-100 ease-linear', styles.progress]"
        :style="{ width: `${progress}%` }"
      />
    </div>
  </div>
</template>
