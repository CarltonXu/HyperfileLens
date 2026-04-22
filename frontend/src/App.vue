<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'

const route = useRoute()
const authStore = useAuthStore()
const appStore = useAppStore()

onMounted(async () => {
  // Initialize application
  await appStore.initialize()

  // Check authentication status
  if (authStore.isAuthenticated) {
    await authStore.fetchUser()
  }
})

// Watch route changes
watch(
  () => route.path,
  () => {
    // Update page title
    const title = route.meta.title as string
    document.title = title
      ? `${title} | HyperFileLens`
      : 'HyperFileLens'
  }
)
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Main Content -->
    <RouterView />

    <!-- Global Loading Overlay -->
    <Transition name="fade">
      <div
        v-if="appStore.isLoading"
        class="fixed inset-0 z-50 flex items-center justify-center bg-white/80 backdrop-blur-sm"
      >
        <div class="text-center">
          <div class="spinner-lg mx-auto mb-4"></div>
          <p class="text-gray-600">{{ appStore.loadingMessage }}</p>
        </div>
      </div>
    </Transition>

    <!-- Toast Notifications -->
    <Teleport to="body">
      <div class="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        <TransitionGroup name="toast">
          <div
            v-for="toast in appStore.toasts"
            :key="toast.id"
            :class="[
              'px-4 py-3 rounded-lg shadow-lg max-w-sm',
              {
                'bg-success-500 text-white': toast.type === 'success',
                'bg-danger-500 text-white': toast.type === 'error',
                'bg-warning-500 text-white': toast.type === 'warning',
                'bg-primary-500 text-white': toast.type === 'info',
              }
            ]"
          >
            <p class="font-medium">{{ toast.title }}</p>
            <p v-if="toast.message" class="text-sm opacity-90">{{ toast.message }}</p>
          </div>
        </TransitionGroup>
      </div>
    </Teleport>
  </div>
</template>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-leave-to {
  opacity: 0;
  transform: translateY(100%);
}
</style>
