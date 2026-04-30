import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import i18n from './i18n'
import { useThemeStore } from './stores/theme'
import './assets/main.css'

// Create Vue application
const app = createApp(App)

// Use plugins
const pinia = createPinia()
app.use(pinia)
app.use(router)
app.use(i18n)

// Initialize theme
const themeStore = useThemeStore()
themeStore.initTheme()

// Mount application
app.mount('#app')
