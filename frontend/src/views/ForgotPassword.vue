<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api'

const { t } = useI18n()

// Steps: 1=输入邮箱, 2=验证码验证, 3=设置新密码, 4=成功
const currentStep = ref(1)

// Step 1: Email
const email = ref('')
const captcha = ref('')
const captchaUrl = ref('')
const captchaKey = ref('')

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
  try {
    const response = await api.get('/accounts/captcha/', { responseType: 'blob' })
    captchaUrl.value = URL.createObjectURL(response.data)
    captchaKey.value = response.headers['x-captcha-key'] || ''
  } catch (err) {
    console.error('Failed to fetch captcha:', err)
  }
}

async function sendResetEmail() {
  if (!isValidStep1.value) return
  
  isLoading.value = true
  error.value = ''
  
  try {
    const response = await api.post('/accounts/password/reset/', {
      email: email.value,
      captcha: captcha.value,
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
    await api.post('/accounts/password/reset/verify/', {
      email: email.value,
      token: resetToken.value,
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
    await api.post('/accounts/password/reset/confirm/', {
      email: email.value,
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
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 py-12 px-4">
    <div class="max-w-md w-full">
      <!-- Logo -->
      <div class="text-center mb-8">
        <router-link to="/login" class="inline-flex items-center justify-center w-16 h-16 bg-primary-600 rounded-2xl mb-4 hover:bg-primary-700 transition-colors">
          <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
          </svg>
        </router-link>
        <h1 class="text-2xl font-bold text-gray-900">{{ t('auth.forgotPassword') }}</h1>
        <p class="text-gray-600 mt-2">{{ t('auth.forgotPasswordSubtitle') }}</p>
      </div>

      <!-- Progress Steps -->
      <div class="flex items-center justify-center mb-8">
        <div class="flex items-center">
          <div :class="['w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium', currentStep >= 1 ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-500']">1</div>
          <div :class="['w-12 h-0.5', currentStep >= 2 ? 'bg-primary-600' : 'bg-gray-200']"></div>
          <div :class="['w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium', currentStep >= 2 ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-500']">2</div>
          <div :class="['w-12 h-0.5', currentStep >= 3 ? 'bg-primary-600' : 'bg-gray-200']"></div>
          <div :class="['w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium', currentStep >= 3 ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-500']">3</div>
          <div :class="['w-12 h-0.5', currentStep >= 4 ? 'bg-primary-600' : 'bg-gray-200']"></div>
          <div :class="['w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium', currentStep >= 4 ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-500']">
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
            </svg>
          </div>
        </div>
      </div>

      <!-- Form Card -->
      <div class="bg-white rounded-2xl shadow-xl p-8">
        <!-- Error Message -->
        <div v-if="error" class="bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded-xl flex items-center gap-2 mb-6">
          <svg class="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
          </svg>
          {{ error }}
        </div>

        <!-- Success Message -->
        <div v-if="success" class="bg-success-50 border border-success-200 text-success-700 px-4 py-3 rounded-xl flex items-center gap-2 mb-6">
          <svg class="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
          </svg>
          {{ success }}
        </div>

        <!-- Step 1: Enter Email -->
        <form v-if="currentStep === 1" @submit.prevent="sendResetEmail" class="space-y-5">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">{{ t('auth.email') }}</label>
            <div class="relative">
              <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                <svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                </svg>
              </div>
              <input
                v-model="email"
                type="email"
                class="w-full pl-11 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                :placeholder="t('auth.emailPlaceholder')"
                required
              />
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">{{ t('auth.captcha') }}</label>
            <div class="flex gap-3">
              <div class="relative flex-1">
                <input
                  v-model="captcha"
                  type="text"
                  maxlength="6"
                  class="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 uppercase tracking-widest"
                  :placeholder="t('auth.captchaPlaceholder')"
                  required
                />
              </div>
              <img
                :src="captchaUrl"
                alt="Captcha"
                class="h-12 w-28 rounded-lg border border-gray-300 cursor-pointer hover:opacity-80 transition-opacity object-cover bg-gray-100"
                @click="refreshCaptcha"
              />
            </div>
          </div>

          <button
            type="submit"
            :disabled="!isValidStep1 || isLoading"
            class="w-full py-3 px-4 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-xl shadow-lg shadow-primary-500/30 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <svg v-if="isLoading" class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
            {{ t('auth.sendResetCode') }}
          </button>
        </form>

        <!-- Step 2: Verify Code -->
        <form v-if="currentStep === 2" @submit.prevent="verifyCode" class="space-y-5">
          <p class="text-sm text-gray-600">{{ t('auth.enterVerificationCode') }}</p>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">{{ t('auth.verificationCode') }}</label>
            <input
              v-model="verificationCode"
              type="text"
              maxlength="6"
              class="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-center text-2xl tracking-widest uppercase"
              :placeholder="t('auth.verificationCodePlaceholder')"
              required
            />
          </div>
          <button
            type="submit"
            :disabled="!isValidStep2 || isLoading"
            class="w-full py-3 px-4 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-xl shadow-lg shadow-primary-500/30 disabled:opacity-50"
          >
            {{ t('auth.verifyCode') }}
          </button>
        </form>

        <!-- Step 3: Set New Password -->
        <form v-if="currentStep === 3" @submit.prevent="resetPassword" class="space-y-5">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">{{ t('auth.newPassword') }}</label>
            <div class="relative">
              <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                <svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
                </svg>
              </div>
              <input
                v-model="newPassword"
                :type="showNewPassword ? 'text' : 'password'"
                class="w-full pl-11 pr-12 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                :placeholder="t('auth.newPasswordPlaceholder')"
                required
              />
              <button
                type="button"
                @click="showNewPassword = !showNewPassword"
                class="absolute inset-y-0 right-0 pr-3.5 flex items-center text-gray-400 hover:text-gray-600"
              >
                <svg v-if="!showNewPassword" class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                </svg>
                <svg v-else class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
                </svg>
              </button>
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">{{ t('auth.confirmPassword') }}</label>
            <div class="relative">
              <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                <svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
                </svg>
              </div>
              <input
                v-model="confirmPassword"
                :type="showConfirmPassword ? 'text' : 'password'"
                class="w-full pl-11 pr-12 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                :class="{'border-danger-500': confirmPassword && newPassword !== confirmPassword}"
                :placeholder="t('auth.confirmPasswordPlaceholder')"
                required
              />
              <button
                type="button"
                @click="showConfirmPassword = !showConfirmPassword"
                class="absolute inset-y-0 right-0 pr-3.5 flex items-center text-gray-400 hover:text-gray-600"
              >
                <svg v-if="!showConfirmPassword" class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                </svg>
                <svg v-else class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
                </svg>
              </button>
            </div>
          </div>

          <button
            type="submit"
            :disabled="!isValidStep3 || isLoading"
            class="w-full py-3 px-4 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-xl shadow-lg shadow-primary-500/30 disabled:opacity-50"
          >
            {{ t('auth.resetPassword') }}
          </button>
        </form>

        <!-- Step 4: Success -->
        <div v-if="currentStep === 4" class="text-center py-6">
          <div class="w-16 h-16 bg-success-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg class="w-8 h-8 text-success-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
            </svg>
          </div>
          <h3 class="text-xl font-semibold text-gray-900 mb-2">{{ t('auth.passwordResetSuccess') }}</h3>
          <p class="text-gray-600 mb-6">{{ t('auth.canNowLogin') }}</p>
          <router-link
            to="/login"
            class="inline-flex items-center justify-center px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-xl"
          >
            {{ t('auth.goToLogin') }}
          </router-link>
        </div>

        <!-- Back to Login -->
        <div v-if="currentStep < 4" class="mt-6 text-center">
          <router-link to="/login" class="text-sm text-gray-600 hover:text-gray-900 flex items-center justify-center gap-1">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
            </svg>
            {{ t('auth.backToLogin') }}
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>
