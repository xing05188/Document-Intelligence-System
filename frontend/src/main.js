import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'

// Import styles in order: theme -> components -> main
import './styles/theme.css'
import './styles/components.css'
import './styles/main.css'

// Initialize theme before app mounts
import { initTheme } from './composables/useTheme'
initTheme()

const app = createApp(App)
app.use(createPinia())
app.mount('#app')
