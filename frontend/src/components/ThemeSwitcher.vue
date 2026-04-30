<script setup lang="ts">
import { ref, computed } from 'vue'
import { useThemeStore, type Theme } from '@/stores/theme'
import { useI18n } from 'vue-i18n'
import {
  SunIcon,
  MoonIcon,
  ComputerDesktopIcon,
  ChevronDownIcon
} from '@heroicons/vue/24/outline'

const { t } = useI18n()
const themeStore = useThemeStore()

const isOpen = ref(false)

const themes: { value: Theme; icon: any; label: string }[] = [
  { value: 'light', icon: SunIcon, label: t('theme.light') },
  { value: 'dark', icon: MoonIcon, label: t('theme.dark') },
  { value: 'system', icon: ComputerDesktopIcon, label: t('theme.system') }
]

const currentTheme = computed(() => themeStore.theme)

const currentIcon = computed(() => {
  const theme = themes.find(t => t.value === currentTheme.value)
  return theme?.icon || ComputerDesktopIcon
})

function selectTheme(theme: Theme) {
  themeStore.setTheme(theme)
  isOpen.value = false
}

function toggleDropdown() {
  isOpen.value = !isOpen.value
}

function closeDropdown() {
  isOpen.value = false
}
</script>

<template>
  <div class="relative" v-click-outside="closeDropdown">
    <button
      @click="toggleDropdown"
      class="flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700 transition-colors"
      :aria-expanded="isOpen"
      aria-haspopup="true"
    >
      <component :is="currentIcon" class="h-5 w-5" />
      <ChevronDownIcon class="h-4 w-4" :class="{ 'rotate-180': isOpen }" />
    </button>

    <Transition
      enter-active-class="transition ease-out duration-100"
      enter-from-class="transform opacity-0 scale-95"
      enter-to-class="transform opacity-100 scale-100"
      leave-active-class="transition ease-in duration-75"
      leave-from-class="transform opacity-100 scale-100"
      leave-to-class="transform opacity-0 scale-95"
    >
      <div
        v-if="isOpen"
        class="absolute right-0 z-50 mt-2 w-36 origin-top-right rounded-lg bg-white dark:bg-slate-800 shadow-lg ring-1 ring-black/5 dark:ring-slate-700 focus:outline-none"
      >
        <div class="py-1">
          <button
            v-for="theme in themes"
            :key="theme.value"
            @click="selectTheme(theme.value)"
            class="flex w-full items-center gap-2 px-3 py-2 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
            :class="{ 'bg-slate-50 dark:bg-slate-700/50': currentTheme === theme.value }"
          >
            <component :is="theme.icon" class="h-4 w-4" />
            <span>{{ theme.label }}</span>
            <svg
              v-if="currentTheme === theme.value"
              class="ml-auto h-4 w-4 text-blue-500"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fill-rule="evenodd"
                d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                clip-rule="evenodd"
              />
            </svg>
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>
