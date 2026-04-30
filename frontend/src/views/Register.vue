<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'
import api from '@/api'

const router = useRouter()
const { t, locale } = useI18n()
const appStore = useAppStore()

function toggleLanguage() {
  const newLocale = locale.value === 'zh-CN' ? 'en' : 'zh-CN'
  locale.value = newLocale
  localStorage.setItem('locale', newLocale)
}

const firstName = ref('')
const lastName = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const captcha = ref('')
const agreedToTerms = ref(false)
const showPassword = ref(false)
const showConfirmPassword = ref(false)
const isLoading = ref(false)
const error = ref('')

const captchaUrl = ref('')
const captchaKey = ref('')

const passwordStrength = computed(() => {
  const pwd = password.value
  if (!pwd) return { score: 0, text: '', color: '' }
  
  let score = 0
  if (pwd.length >= 8) score++
  if (/[A-Z]/.test(pwd)) score++
  if (/[a-z]/.test(pwd)) score++
  if (/[0-9]/.test(pwd)) score++
  if (/[^A-Za-z0-9]/.test(pwd)) score++
  
  const levels = [
    { text: t('auth.veryWeak'), color: 'bg-red-500' },
    { text: t('auth.weak'), color: 'bg-orange-500' },
    { text: t('auth.fair'), color: 'bg-yellow-500' },
    { text: t('auth.good'), color: 'bg-lime-500' },
    { text: t('auth.strong'), color: 'bg-green-500' },
    { text: t('auth.veryStrong'), color: 'bg-emerald-500' }
  ]
  
  return { score, ...levels[score] }
})

const isValid = computed(() => {
  return (
    firstName.value.length > 0 &&
    lastName.value.length > 0 &&
    email.value.length > 0 &&
    password.value.length >= 6 &&
    password.value === confirmPassword.value &&
    captcha.value.length > 0 &&
    agreedToTerms.value
  )
})

async function refreshCaptcha() {
  try {
    const response = await api.get('/api/v1/accounts/captcha/')
    captchaUrl.value = response.data.image
    captchaKey.value = response.data.key
  } catch (err) {
    console.error('Failed to fetch captcha:', err)
  }
}

async function handleRegister() {
  if (!isValid.value) return
  isLoading.value = true
  error.value = ''

  try {
    await api.post('/api/v1/accounts/register-v2/', {
      email: email.value,
      password: password.value,
      first_name: firstName.value,
      last_name: lastName.value,
      captcha_code: captcha.value,
      captcha_key: captchaKey.value
    })
    
    appStore.showToast({
      type: 'success',
      title: t('auth.registerSuccess'),
      message: t('auth.canNowLogin')
    })
    
    router.push('/login')
  } catch (err: any) {
    error.value = err.response?.data?.error || t('auth.registerFailed')
    refreshCaptcha()
    captcha.value = ''
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
        <div class="inline-flex items-center justify-center w-10 h-10 bg-emerald-600 rounded-lg mb-3">
          <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
          </svg>
        </div>
        <h1 class="text-xl font-semibold text-slate-900">{{ t('auth.createAccount') }}</h1>
        <p class="text-sm text-slate-500 mt-1">{{ t('auth.registerSubtitle') }}</p>
      </div>

      <!-- Register Card -->
      <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
        <form @submit.prevent="handleRegister" class="space-y-4">
          <!-- Error -->
          <div v-if="error" class="bg-red-50 border border-red-200 text-red-600 text-sm px-3 py-2 rounded-lg">
            {{ error }}
          </div>

          <!-- Name -->
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-sm text-slate-600 mb-1">{{ t('auth.firstName') }}</label>
              <input
                v-model="firstName"
                type="text"
                class="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                :placeholder="t('auth.firstNamePlaceholder')"
                required
              />
            </div>
            <div>
              <label class="block text-sm text-slate-600 mb-1">{{ t('auth.lastName') }}</label>
              <input
                v-model="lastName"
                type="text"
                class="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                :placeholder="t('auth.lastNamePlaceholder')"
                required
              />
            </div>
          </div>

          <!-- Email -->
          <div>
            <label class="block text-sm text-slate-600 mb-1">{{ t('auth.email') }}</label>
            <input
              v-model="email"
              type="email"
              class="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
              :placeholder="t('auth.emailPlaceholder')"
              required
            />
          </div>

          <!-- Password -->
          <div>
            <label class="block text-sm text-slate-600 mb-1">{{ t('auth.password') }}</label>
            <div class="relative">
              <input
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                class="w-full px-3 py-2 pr-9 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                :placeholder="t('auth.passwordPlaceholder')"
                required
                minlength="6"
              />
              <button
                type="button"
                @click="showPassword = !showPassword"
                class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                <svg v-if="!showPassword" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                </svg>
                <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
                </svg>
              </button>
            </div>
            <!-- Password Strength -->
            <div v-if="password" class="flex items-center gap-2 mt-1.5">
              <div class="flex-1 h-1 bg-slate-200 rounded-full overflow-hidden">
                <div 
                  :class="passwordStrength.color"
                  class="h-full transition-all duration-300"
                  :style="{ width: `${(passwordStrength.score / 5) * 100}%` }"
                ></div>
              </div>
              <span class="text-xs text-slate-500 w-10">{{ passwordStrength.text }}</span>
            </div>
          </div>

          <!-- Confirm Password -->
          <div>
            <label class="block text-sm text-slate-600 mb-1">{{ t('auth.confirmPassword') }}</label>
            <div class="relative">
              <input
                v-model="confirmPassword"
                :type="showConfirmPassword ? 'text' : 'password'"
                class="w-full px-3 py-2 pr-9 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                :class="{ 'border-red-300 focus:ring-red-500': confirmPassword && password !== confirmPassword }"
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
            <p v-if="confirmPassword && password !== confirmPassword" class="text-xs text-red-500 mt-1">
              {{ t('auth.passwordMismatch') }}
            </p>
          </div>

          <!-- Captcha -->
          <div>
            <label class="block text-sm text-slate-600 mb-1">{{ t('auth.captcha') }}</label>
            <div class="flex gap-2">
              <input
                v-model="captcha"
                type="text"
                maxlength="6"
                class="flex-1 px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent uppercase tracking-wider text-center"
                :placeholder="t('auth.captchaPlaceholder')"
                required
              />
              <img
                :src="captchaUrl"
                alt="Captcha"
                class="h-9 w-24 rounded-lg border border-slate-200 cursor-pointer hover:opacity-80 transition-opacity bg-slate-50"
                @click="refreshCaptcha"
                :title="t('auth.refreshCaptcha')"
              />
            </div>
          </div>

          <!-- Terms -->
          <label class="flex items-start gap-2 cursor-pointer">
            <input
              v-model="agreedToTerms"
              type="checkbox"
              class="mt-0.5 w-3.5 h-3.5 rounded border-slate-300 text-emerald-600"
            />
            <span class="text-xs text-slate-500">
              {{ t('auth.agreeToTerms') }}
              <a href="#" class="text-emerald-600 hover:text-emerald-700">{{ t('auth.termsOfService') }}</a>
              {{ t('auth.and') }}
              <a href="#" class="text-emerald-600 hover:text-emerald-700">{{ t('auth.privacyPolicy') }}</a>
            </span>
          </label>

          <!-- Submit -->
          <button
            type="submit"
            class="w-full py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="!isValid || isLoading"
          >
            {{ isLoading ? t('auth.creatingAccount') : t('auth.createAccount') }}
          </button>
        </form>

        <!-- Divider -->
        <div class="relative my-4">
          <div class="absolute inset-0 flex items-center">
            <div class="w-full border-t border-slate-200"></div>
          </div>
          <div class="relative flex justify-center text-xs">
            <span class="px-2 bg-white text-slate-400">{{ t('auth.or') }}</span>
          </div>
        </div>

        <!-- Login Link -->
        <p class="text-center text-sm text-slate-500">
          {{ t('auth.alreadyHaveAccount') }}
          <router-link to="/login" class="text-emerald-600 hover:text-emerald-700 font-medium">
            {{ t('auth.loginNow') }}
          </router-link>
        </p>
      </div>

      <!-- Footer -->
      <p class="text-center text-xs text-slate-400 mt-4">
        &copy; 2024 HyperFileLens
      </p>
    </div>
  </div>
</template>
