<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api'

const { t, locale } = useI18n()

function toggleLanguage() {
  const newLocale = locale.value === 'zh-CN' ? 'en' : 'zh-CN'
  locale.value = newLocale
  localStorage.setItem('locale', newLocale)
}

// Steps: 1=输入邮箱, 2=验证码验证, 3=设置新密码, 4=成功
const currentStep = ref(1)

// Step 1: Email
const email = ref('')
const captcha = ref('')
const captchaUrl = ref('')
const captchaKey = ref('')
const captchaLoading = ref(false)

// Step 2: Verification code
const verificationCode = ref('')
const resetToken = ref('')

// Step 3: New password
const newPassword = ref('')
const confirmPassword = ref('')
const showNewPassword = ref(false)
const showConfirmPassword = ref(false)

const isLoading = ref(false)
const error = ref('')
const success = ref('')

const isValidStep1 = computed(() => email.value.length > 0 && captcha.value.length > 0)
const isValidStep2 = computed(() => verificationCode.value.length >= 6)
const isValidStep3 = computed(() => newPassword.value.length >= 8 && newPassword.value === confirmPassword.value)

async function refreshCaptcha() {
  captchaLoading.value = true
  try {
    const response = await api.get('/api/v1/accounts/captcha/')
    captchaUrl.value = response.data.image
    captchaKey.value = response.data.key
  } catch (err) {
    console.error('Failed to fetch captcha:', err)
  } finally {
    captchaLoading.value = false
  }
}

async function sendResetEmail() {
  if (!isValidStep1.value) return
  
  isLoading.value = true
  error.value = ''
  success.value = ''
  
  try {
    const response = await api.post('/api/v1/accounts/forgot-password/', {
      email: email.value,
      captcha_code: captcha.value,
      captcha_key: captchaKey.value
    })
    resetToken.value = response.data.reset_token
    currentStep.value = 2
    success.value = t('auth.resetCodeSent')
  } catch (err: any) {
    error.value = err.response?.data?.error || t('auth.sendResetFailed')
    refreshCaptcha()
    captcha.value = ''
  } finally {
    isLoading.value = false
  }
}

async function verifyCode() {
  if (!isValidStep2.value) return
  
  isLoading.value = true
  error.value = ''
  
  try {
    await api.post('/api/v1/accounts/verify-reset-code/', {
      email: email.value,
      code: verificationCode.value
    })
    currentStep.value = 3
    success.value = t('auth.codeVerified')
  } catch (err: any) {
    error.value = err.response?.data?.error || t('auth.invalidCode')
    verificationCode.value = ''
  } finally {
    isLoading.value = false
  }
}

async function resetPassword() {
  if (!isValidStep3.value) return
  
  if (newPassword.value !== confirmPassword.value) {
    error.value = t('auth.passwordMismatch')
    return
  }
  
  isLoading.value = true
  error.value = ''
  
  try {
    await api.post('/api/v1/accounts/reset-password/', {
      token: resetToken.value,
      new_password: newPassword.value
    })
    currentStep.value = 4
    success.value = t('auth.passwordResetSuccess')
  } catch (err: any) {
    error.value = err.response?.data?.error || t('auth.resetPasswordFailed')
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  refreshCaptcha()
})
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-slate-100 p-4">
    <!-- Language Switch -->
    <button
      @click="toggleLanguage"
      class="fixed top-4 right-4 flex items-center gap-1.5 px-3 py-1.5 text-sm text-slate-500 hover:text-slate-700 transition-colors"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129"/>
      </svg>
      {{ locale === 'zh-CN' ? 'EN' : '中文' }}
    </button>

    <div class="w-full max-w-sm">
      <!-- Logo & Title -->
      <div class="text-center mb-6">
        <router-link to="/login" class="inline-flex items-center justify-center w-10 h-10 bg-indigo-600 rounded-lg mb-3 hover:bg-indigo-700 transition-colors">
          <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
          </svg>
        </router-link>
        <h1 class="text-xl font-semibold text-slate-900">{{ t('auth.forgotPassword') }}</h1>
        <p class="text-sm text-slate-500 mt-1">{{ t('auth.forgotPasswordSubtitle') }}</p>
      </div>

      <!-- Progress Steps -->
      <div class="flex items-center justify-center gap-1 mb-5">
        <div :class="['w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium transition-colors', currentStep >= 1 ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-500']">1</div>
        <div :class="['w-8 h-0.5 transition-colors', currentStep >= 2 ? 'bg-indigo-600' : 'bg-slate-200']"></div>
        <div :class="['w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium transition-colors', currentStep >= 2 ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-500']">2</div>
        <div :class="['w-8 h-0.5 transition-colors', currentStep >= 3 ? 'bg-indigo-600' : 'bg-slate-200']"></div>
        <div :class="['w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium transition-colors', currentStep >= 3 ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-500']">3</div>
        <div :class="['w-8 h-0.5 transition-colors', currentStep >= 4 ? 'bg-indigo-600' : 'bg-slate-200']"></div>
        <div :class="['w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium transition-colors', currentStep >= 4 ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-500']">
          <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
          </svg>
        </div>
      </div>

      <!-- Form Card -->
      <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
        <!-- Error Message -->
        <div v-if="error" class="bg-red-50 border border-red-200 text-red-600 text-sm px-3 py-2 rounded-lg mb-4">
          {{ error }}
        </div>

        <!-- Success Message -->
        <div v-if="success" class="bg-green-50 border border-green-200 text-green-600 text-sm px-3 py-2 rounded-lg mb-4">
          {{ success }}
        </div>

        <!-- Step 1: Enter Email -->
        <form v-if="currentStep === 1" @submit.prevent="sendResetEmail" class="space-y-4">
          <div>
            <label class="block text-sm text-slate-600 mb-1">{{ t('auth.email') }}</label>
            <input
              v-model="email"
              type="email"
              class="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              :placeholder="t('auth.emailPlaceholder')"
              required
            />
          </div>

          <div>
            <label class="block text-sm text-slate-600 mb-1">{{ t('auth.captcha') }}</label>
            <div class="flex gap-2">
              <input
                v-model="captcha"
                type="text"
                maxlength="6"
                class="flex-1 px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent uppercase tracking-wider text-center"
                :placeholder="t('auth.captchaPlaceholder')"
                required
              />
              <div class="relative h-9 w-24 rounded-lg border border-slate-200 bg-slate-50 cursor-pointer overflow-hidden" @click="refreshCaptcha" :title="t('auth.refreshCaptcha')">
                <img
                  v-if="captchaUrl"
                  :src="captchaUrl"
                  alt="Captcha"
                  class="h-full w-full object-cover"
                />
                <div v-if="captchaLoading" class="absolute inset-0 bg-slate-100/80 flex items-center justify-center">
                  <svg class="w-4 h-4 text-slate-400 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                </div>
                <div v-if="!captchaUrl && !captchaLoading" class="h-full w-full flex items-center justify-center text-slate-400">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                </div>
              </div>
            </div>
          </div>

          <button
            type="submit"
            :disabled="!isValidStep1 || isLoading"
            class="w-full py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ t('auth.sendResetCode') }}
          </button>
        </form>

        <!-- Step 2: Verify Code -->
        <form v-if="currentStep === 2" @submit.prevent="verifyCode" class="space-y-4">
          <p class="text-sm text-slate-500">{{ t('auth.enterVerificationCode') }}</p>
          <div>
            <label class="block text-sm text-slate-600 mb-1">{{ t('auth.verificationCode') }}</label>
            <input
              v-model="verificationCode"
              type="text"
              maxlength="6"
              class="w-full px-3 py-2 text-lg border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-center tracking-widest uppercase"
              :placeholder="t('auth.verificationCodePlaceholder')"
              required
            />
          </div>
          <button
            type="submit"
            :disabled="!isValidStep2 || isLoading"
            class="w-full py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ t('auth.verifyCode') }}
          </button>
        </form>

        <!-- Step 3: Set New Password -->
        <form v-if="currentStep === 3" @submit.prevent="resetPassword" class="space-y-4">
          <div>
            <label class="block text-sm text-slate-600 mb-1">{{ t('auth.newPassword') }}</label>
            <div class="relative">
              <input
                v-model="newPassword"
                :type="showNewPassword ? 'text' : 'password'"
                class="w-full px-3 py-2 pr-9 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                :placeholder="t('auth.newPasswordPlaceholder')"
                required
              />
              <button
                type="button"
                @click="showNewPassword = !showNewPassword"
                class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                <svg v-if="!showNewPassword" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                </svg>
                <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
                </svg>
              </button>
            </div>
          </div>

          <div>
            <label class="block text-sm text-slate-600 mb-1">{{ t('auth.confirmPassword') }}</label>
            <div class="relative">
              <input
                v-model="confirmPassword"
                :type="showConfirmPassword ? 'text' : 'password'"
                class="w-full px-3 py-2 pr-9 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                :class="confirmPassword && newPassword !== confirmPassword ? 'border-red-300' : 'border-slate-200'"
                :placeholder="t('auth.confirmPasswordPlaceholder')"
                required
              />
              <button
                type="button"
                @click="showConfirmPassword = !showConfirmPassword"
                class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                <svg v-if="!showConfirmPassword" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                </svg>
                <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
                </svg>
              </button>
            </div>
            <p v-if="confirmPassword && newPassword !== confirmPassword" class="text-xs text-red-500 mt-1">
              {{ t('auth.passwordMismatch') }}
            </p>
          </div>

          <button
            type="submit"
            :disabled="!isValidStep3 || isLoading"
            class="w-full py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ t('auth.resetPassword') }}
          </button>
        </form>

        <!-- Step 4: Success -->
        <div v-if="currentStep === 4" class="text-center py-4">
          <div class="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
            <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
            </svg>
          </div>
          <h3 class="text-lg font-medium text-slate-900 mb-1">{{ t('auth.passwordResetSuccess') }}</h3>
          <p class="text-sm text-slate-500 mb-4">{{ t('auth.canNowLogin') }}</p>
          <router-link
            to="/login"
            class="inline-flex items-center justify-center px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors"
          >
            {{ t('auth.goToLogin') }}
          </router-link>
        </div>

        <!-- Back to Login -->
        <div v-if="currentStep < 4" class="mt-4 pt-4 border-t border-slate-100 text-center">
          <router-link to="/login" class="text-sm text-slate-500 hover:text-slate-700 inline-flex items-center gap-1">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
            </svg>
            {{ t('auth.backToLogin') }}
          </router-link>
        </div>
      </div>

      <!-- Footer -->
      <p class="text-center text-xs text-slate-400 mt-4">
        &copy; 2024 HyperFileLens
      </p>
    </div>
  </div>
</template>
