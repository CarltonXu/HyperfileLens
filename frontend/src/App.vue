<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import Toast from '@/components/Toast.vue'

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
 <div class="min-h-screen app-background">
 <!-- Main Content -->
 <RouterView />

 <!-- Global Loading Overlay -->
 <Transition name="fade">
 <div
 v-if="appStore.isLoading"
 class="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm"
 >
 <div class="text-center">
 <div class="spinner-lg mx-auto mb-4"></div>
 <p class="text-foreground-secondary">{{ appStore.loadingMessage }}</p>
 </div>
 </div>
 </Transition>

 <!-- Toast Notifications -->
 <Teleport to="body">
 <div class="fixed top-4 right-4 z-[100] flex flex-col gap-3 pointer-events-none">
 <TransitionGroup name="toast">
 <Toast
 v-for="toast in appStore.toasts"
 :key="toast.id"
 v-bind="toast"
 @close="appStore.removeToast"
 />
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

.toast-enter-active {
 animation: toast-in 0.3s ease-out;
}

.toast-leave-active {
 animation: toast-out 0.2s ease-in forwards;
}

@keyframes toast-in {
 from {
 opacity: 0;
 transform: translateX(100%) scale(0.9);
 }
 to {
 opacity: 1;
 transform: translateX(0) scale(1);
 }
}

@keyframes toast-out {
 from {
 opacity: 1;
 transform: translateX(0) scale(1);
 }
 to {
 opacity: 0;
 transform: translateX(100%) scale(0.9);
 }
}
</style>
