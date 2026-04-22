<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'

const { t, locale } = useI18n()
const authStore = useAuthStore()
const appStore = useAppStore()

const activeTab = ref('profile')

const profile = ref({
  first_name: authStore.user?.first_name || '',
  last_name: authStore.user?.last_name || '',
  email: authStore.user?.email || '',
  phone: authStore.user?.phone || ''
})

function setTheme(theme: 'light' | 'dark') {
  appStore.setTheme(theme)
}

function setLocale(newLocale: string) {
  locale.value = newLocale
  localStorage.setItem('locale', newLocale)
}
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-2xl font-bold text-gray-900">{{ t('settings.title') }}</h1>
      <p class="text-gray-500 mt-1">{{ t('settings.subtitle') }}</p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
      <!-- Sidebar -->
      <div class="lg:col-span-1">
        <nav class="space-y-1">
          <button
            v-for="tab in ['profile', 'security', 'appearance', 'language']"
            :key="tab"
            :class="[
              'w-full text-left px-4 py-2 rounded-lg',
              activeTab === tab
                ? 'bg-primary-50 text-primary-700 font-medium'
                : 'text-gray-600 hover:bg-gray-100'
            ]"
            @click="activeTab = tab"
          >
            {{ t(`settings.sections.${tab}`) }}
          </button>
        </nav>
      </div>

      <!-- Content -->
      <div class="lg:col-span-3">
        <!-- Profile -->
        <div v-if="activeTab === 'profile'" class="card">
          <div class="card-header">
            <h3 class="text-lg font-semibold">{{ t('settings.profile.title') }}</h3>
          </div>
          <div class="card-body space-y-4">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="label">{{ t('settings.profile.firstName') }}</label>
                <input v-model="profile.first_name" type="text" class="input" />
              </div>
              <div>
                <label class="label">{{ t('settings.profile.lastName') }}</label>
                <input v-model="profile.last_name" type="text" class="input" />
              </div>
            </div>
            <div>
              <label class="label">{{ t('settings.profile.email') }}</label>
              <input v-model="profile.email" type="email" class="input" disabled />
            </div>
            <div>
              <label class="label">{{ t('settings.profile.phone') }}</label>
              <input v-model="profile.phone" type="tel" class="input" />
            </div>
            <div class="flex justify-end">
              <button class="btn-primary">{{ t('common.save') }}</button>
            </div>
          </div>
        </div>

        <!-- Security -->
        <div v-if="activeTab === 'security'" class="card">
          <div class="card-header">
            <h3 class="text-lg font-semibold">{{ t('settings.security.title') }}</h3>
          </div>
          <div class="card-body space-y-4">
            <div>
              <label class="label">{{ t('settings.security.currentPassword') }}</label>
              <input type="password" class="input" />
            </div>
            <div>
              <label class="label">{{ t('settings.security.newPassword') }}</label>
              <input type="password" class="input" />
            </div>
            <div>
              <label class="label">{{ t('settings.security.confirmPassword') }}</label>
              <input type="password" class="input" />
            </div>
            <div class="flex justify-end">
              <button class="btn-primary">{{ t('settings.security.changePassword') }}</button>
            </div>
          </div>
        </div>

        <!-- Appearance -->
        <div v-if="activeTab === 'appearance'" class="card">
          <div class="card-header">
            <h3 class="text-lg font-semibold">{{ t('settings.appearance.title') }}</h3>
          </div>
          <div class="card-body">
            <div class="space-y-4">
              <div>
                <label class="label">{{ t('settings.appearance.theme') }}</label>
                <div class="flex gap-4">
                  <button
                    :class="[
                      'flex-1 p-4 rounded-lg border-2 transition-colors',
                      appStore.theme === 'light' ? 'border-primary-500 bg-primary-50' : 'border-gray-200'
                    ]"
                    @click="setTheme('light')"
                  >
                    <div class="w-6 h-6 bg-white rounded mb-2"></div>
                    <span class="text-sm">{{ t('settings.appearance.light') }}</span>
                  </button>
                  <button
                    :class="[
                      'flex-1 p-4 rounded-lg border-2 transition-colors',
                      appStore.theme === 'dark' ? 'border-primary-500 bg-primary-50' : 'border-gray-200'
                    ]"
                    @click="setTheme('dark')"
                  >
                    <div class="w-6 h-6 bg-gray-800 rounded mb-2"></div>
                    <span class="text-sm">{{ t('settings.appearance.dark') }}</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Language -->
        <div v-if="activeTab === 'language'" class="card">
          <div class="card-header">
            <h3 class="text-lg font-semibold">{{ t('settings.language.title') }}</h3>
          </div>
          <div class="card-body">
            <div class="space-y-4">
              <button
                :class="[
                  'w-full flex items-center justify-between p-4 rounded-lg border-2 transition-colors',
                  locale === 'en' ? 'border-primary-500 bg-primary-50' : 'border-gray-200'
                ]"
                @click="setLocale('en')"
              >
                <span>{{ t('settings.language.english') }}</span>
                <span v-if="locale === 'en'" class="text-primary-600">✓</span>
              </button>
              <button
                :class="[
                  'w-full flex items-center justify-between p-4 rounded-lg border-2 transition-colors',
                  locale === 'zh-CN' ? 'border-primary-500 bg-primary-50' : 'border-gray-200'
                ]"
                @click="setLocale('zh-CN')"
              >
                <span>{{ t('settings.language.chinese') }}</span>
                <span v-if="locale === 'zh-CN'" class="text-primary-600">✓</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
