<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import {
  XMarkIcon,
  UserCircleIcon,
  KeyIcon,
  LanguageIcon,
  CheckIcon
} from '@heroicons/vue/24/outline'

defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const { t, locale } = useI18n()
const authStore = useAuthStore()

// 当前活动的标签页
const activeTab = ref<'profile' | 'password' | 'preferences'>('profile')

// 修改密码表单
const passwordForm = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})
const passwordError = ref('')
const passwordSuccess = ref(false)
const isChangingPassword = ref(false)

// 用户偏好设置
const preferences = ref({
  language: locale.value,
  theme: 'light'
})

// 计算用户信息
const userInfo = computed(() => ({
  name: authStore.userFullName,
  email: authStore.user?.email || '',
  role: authStore.user?.role?.name || 'User',
  createdAt: authStore.user?.date_joined || ''
}))

// 切换标签页
function switchTab(tab: 'profile' | 'password' | 'preferences') {
  activeTab.value = tab
  passwordError.value = ''
  passwordSuccess.value = false
}

// 关闭弹窗
function closeModal() {
  emit('close')
  // 重置表单
  passwordForm.value = {
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  }
  passwordError.value = ''
  passwordSuccess.value = false
  activeTab.value = 'profile'
}

// 修改密码
async function changePassword() {
  passwordError.value = ''
  passwordSuccess.value = false

  // 验证
  if (!passwordForm.value.currentPassword) {
    passwordError.value = t('profile.currentPasswordRequired')
    return
  }
  if (!passwordForm.value.newPassword) {
    passwordError.value = t('profile.newPasswordRequired')
    return
  }
  if (passwordForm.value.newPassword.length < 8) {
    passwordError.value = t('profile.passwordTooShort')
    return
  }
  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    passwordError.value = t('profile.passwordMismatch')
    return
  }

  isChangingPassword.value = true

  try {
    // TODO: 调用后端 API 修改密码
    // await authStore.changePassword(passwordForm.value.currentPassword, passwordForm.value.newPassword)
    
    // 模拟 API 调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    passwordSuccess.value = true
    passwordForm.value = {
      currentPassword: '',
      newPassword: '',
      confirmPassword: ''
    }
  } catch (error: any) {
    passwordError.value = error.response?.data?.message || t('profile.passwordChangeFailed')
  } finally {
    isChangingPassword.value = false
  }
}

// 保存偏好设置
function savePreferences() {
  locale.value = preferences.value.language
  localStorage.setItem('locale', preferences.value.language)
  // TODO: 保存其他偏好设置到后端
  closeModal()
}

// 格式化日期
function formatDate(dateString: string) {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleDateString(locale.value === 'zh-CN' ? 'zh-CN' : 'en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-[100] overflow-y-auto"
        aria-labelledby="modal-title"
        role="dialog"
        aria-modal="true"
      >
        <!-- 背景遮罩 -->
        <div
          class="fixed inset-0 bg-black/50 transition-opacity"
          @click="closeModal"
        ></div>

        <!-- 模态框内容 -->
        <div class="flex min-h-full items-center justify-center p-4">
          <div
            class="relative bg-white rounded-xl shadow-2xl w-full max-w-lg transform transition-all"
            @click.stop
          >
            <!-- 头部 -->
            <div class="flex items-center justify-between px-6 py-4 border-b border-slate-200">
              <h3 class="text-lg font-semibold text-slate-900">
                {{ t('profile.title') }}
              </h3>
              <button
                @click="closeModal"
                class="p-1 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
              >
                <XMarkIcon class="w-5 h-5" />
              </button>
            </div>

            <!-- 标签页导航 -->
            <div class="flex border-b border-slate-200">
              <button
                @click="switchTab('profile')"
                :class="[
                  'flex-1 px-4 py-3 text-sm font-medium transition-colors',
                  activeTab === 'profile'
                    ? 'text-indigo-600 border-b-2 border-indigo-600'
                    : 'text-slate-500 hover:text-slate-700'
                ]"
              >
                <UserCircleIcon class="w-5 h-5 mx-auto mb-1" />
                {{ t('profile.tabs.profile') }}
              </button>
              <button
                @click="switchTab('password')"
                :class="[
                  'flex-1 px-4 py-3 text-sm font-medium transition-colors',
                  activeTab === 'password'
                    ? 'text-indigo-600 border-b-2 border-indigo-600'
                    : 'text-slate-500 hover:text-slate-700'
                ]"
              >
                <KeyIcon class="w-5 h-5 mx-auto mb-1" />
                {{ t('profile.tabs.password') }}
              </button>
              <button
                @click="switchTab('preferences')"
                :class="[
                  'flex-1 px-4 py-3 text-sm font-medium transition-colors',
                  activeTab === 'preferences'
                    ? 'text-indigo-600 border-b-2 border-indigo-600'
                    : 'text-slate-500 hover:text-slate-700'
                ]"
              >
                <LanguageIcon class="w-5 h-5 mx-auto mb-1" />
                {{ t('profile.tabs.preferences') }}
              </button>
            </div>

            <!-- 内容区域 -->
            <div class="p-6">
              <!-- 个人信息标签页 -->
              <div v-if="activeTab === 'profile'" class="space-y-4">
                <!-- 头像 -->
                <div class="flex justify-center">
                  <div class="w-20 h-20 bg-gradient-to-br from-indigo-400 to-purple-500 rounded-full flex items-center justify-center shadow-lg">
                    <span class="text-2xl font-bold text-white">
                      {{ userInfo.email?.[0]?.toUpperCase() || 'U' }}
                    </span>
                  </div>
                </div>

                <!-- 信息列表 -->
                <div class="space-y-3">
                  <div class="flex items-center justify-between py-2 border-b border-slate-100">
                    <span class="text-sm text-slate-500">{{ t('profile.name') }}</span>
                    <span class="text-sm font-medium text-slate-900">{{ userInfo.name }}</span>
                  </div>
                  <div class="flex items-center justify-between py-2 border-b border-slate-100">
                    <span class="text-sm text-slate-500">{{ t('profile.email') }}</span>
                    <span class="text-sm font-medium text-slate-900">{{ userInfo.email }}</span>
                  </div>
                  <div class="flex items-center justify-between py-2 border-b border-slate-100">
                    <span class="text-sm text-slate-500">{{ t('profile.role') }}</span>
                    <span class="text-sm font-medium text-slate-900">{{ userInfo.role }}</span>
                  </div>
                  <div class="flex items-center justify-between py-2 border-b border-slate-100">
                    <span class="text-sm text-slate-500">{{ t('profile.createdAt') }}</span>
                    <span class="text-sm font-medium text-slate-900">{{ formatDate(userInfo.createdAt) }}</span>
                  </div>
                </div>
              </div>

              <!-- 修改密码标签页 -->
              <div v-if="activeTab === 'password'" class="space-y-4">
                <!-- 成功消息 -->
                <div
                  v-if="passwordSuccess"
                  class="flex items-center gap-2 p-3 bg-green-50 text-green-700 rounded-lg text-sm"
                >
                  <CheckIcon class="w-5 h-5" />
                  {{ t('profile.passwordChanged') }}
                </div>

                <!-- 错误消息 -->
                <div
                  v-if="passwordError"
                  class="flex items-center gap-2 p-3 bg-red-50 text-red-700 rounded-lg text-sm"
                >
                  <XMarkIcon class="w-5 h-5" />
                  {{ passwordError }}
                </div>

                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">
                    {{ t('profile.currentPassword') }}
                  </label>
                  <input
                    v-model="passwordForm.currentPassword"
                    type="password"
                    class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    :placeholder="t('profile.currentPasswordPlaceholder')"
                  />
                </div>
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">
                    {{ t('profile.newPassword') }}
                  </label>
                  <input
                    v-model="passwordForm.newPassword"
                    type="password"
                    class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    :placeholder="t('profile.newPasswordPlaceholder')"
                  />
                </div>
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">
                    {{ t('profile.confirmPassword') }}
                  </label>
                  <input
                    v-model="passwordForm.confirmPassword"
                    type="password"
                    class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    :placeholder="t('profile.confirmPasswordPlaceholder')"
                  />
                </div>

                <button
                  @click="changePassword"
                  :disabled="isChangingPassword"
                  class="w-full py-2 px-4 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {{ isChangingPassword ? t('profile.changing') : t('profile.changePassword') }}
                </button>
              </div>

              <!-- 偏好设置标签页 -->
              <div v-if="activeTab === 'preferences'" class="space-y-4">
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-2">
                    {{ t('profile.language') }}
                  </label>
                  <div class="flex gap-3">
                    <button
                      @click="preferences.language = 'zh-CN'"
                      :class="[
                        'flex-1 py-2 px-4 rounded-lg border transition-colors',
                        preferences.language === 'zh-CN'
                          ? 'border-indigo-600 bg-indigo-50 text-indigo-600'
                          : 'border-slate-300 hover:border-slate-400'
                      ]"
                    >
                      简体中文
                    </button>
                    <button
                      @click="preferences.language = 'en'"
                      :class="[
                        'flex-1 py-2 px-4 rounded-lg border transition-colors',
                        preferences.language === 'en'
                          ? 'border-indigo-600 bg-indigo-50 text-indigo-600'
                          : 'border-slate-300 hover:border-slate-400'
                      ]"
                    >
                      English
                    </button>
                  </div>
                </div>

                <button
                  @click="savePreferences"
                  class="w-full py-2 px-4 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                >
                  {{ t('profile.savePreferences') }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .relative,
.modal-leave-active .relative {
  transition: transform 0.2s ease;
}

.modal-enter-from .relative {
  transform: scale(0.95);
}

.modal-leave-to .relative {
  transform: scale(0.95);
}
</style>
