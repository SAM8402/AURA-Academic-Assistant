import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

// ✅ Tailwind
import './style.css'

// ✅ Bootstrap
import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap-icons/font/bootstrap-icons.css'

const app = createApp(App)
const pinia = createPinia()

// Register plugins
app.use(pinia)
app.use(router)

// Initialize theme from localStorage
import { useThemeStore } from './stores/theme'
const themeStore = useThemeStore()
themeStore.initTheme()

// Initialize authentication from localStorage
import { useUserStore } from './stores/user'
const userStore = useUserStore()
userStore.initializeAuth()

app.mount('#app')
