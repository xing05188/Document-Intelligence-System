import { ref, onMounted, watch } from 'vue'
import { useAuthStore } from '../stores/authStore'

/**
 * Theme Management Composable
 * 支持浅色/深色主题切换，带本地存储持久化和系统偏好侦听
 */

// 全局主题状态（Pinia 替代品，或可集成到 Pinia）
let globalTheme = ref('light')
const STORAGE_KEY = 'app_theme'
const SYSTEM_PREF_KEY = 'prefers-color-scheme'

/**
 * 获取系统主题偏好
 */
function getSystemTheme() {
  if (typeof window === 'undefined') return 'light'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

/**
 * 获取初始主题
 * 优先级：本地存储 > 系统偏好 > 默认浅色
 */
function getInitialTheme() {
  // 1. 检查本地存储
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored && ['light', 'dark'].includes(stored)) {
    return stored
  }
  // 2. 检查系统偏好
  return getSystemTheme()
}

/**
 * 应用主题到 DOM
 */
function applyTheme(theme) {
  const html = document.documentElement
  html.setAttribute('data-theme', theme)
  localStorage.setItem(STORAGE_KEY, theme)
  globalTheme.value = theme
}

/**
 * 切换主题
 */
function toggleTheme() {
  const newTheme = globalTheme.value === 'light' ? 'dark' : 'light'
  setTheme(newTheme)
}

/**
 * 设置主题
 */
function setTheme(theme) {
  if (!['light', 'dark'].includes(theme)) return
  applyTheme(theme)
}

/**
 * Vue Composable Hook
 */
export function useTheme() {
  const theme = ref(globalTheme.value)
  const authStore = useAuthStore()

  onMounted(() => {
    // 初始化主题
    const initialTheme = getInitialTheme()
    applyTheme(initialTheme)
    theme.value = initialTheme

    // 侦听系统主题变化（仅在未显式设置时）
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = (e) => {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (!stored) {
        const newTheme = e.matches ? 'dark' : 'light'
        applyTheme(newTheme)
        theme.value = newTheme
      }
    }
    
    // 兼容旧版浏览器
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange)
    } else if (mediaQuery.addListener) {
      mediaQuery.addListener(handleChange)
    }
  })

  // 监听全局主题状态变化
  watch(globalTheme, (newTheme) => {
    theme.value = newTheme
  })

  return {
    theme,
    toggleTheme,
    setTheme,
    isDark: () => theme.value === 'dark',
    isLight: () => theme.value === 'light'
  }
}

/**
 * 导出全局方法（在 main.js 中使用）
 */
export function initTheme() {
  if (typeof window === 'undefined') return
  
  // 防止页面加载时的闪烁
  const html = document.documentElement
  html.classList.add('no-transition')
  
  const initialTheme = getInitialTheme()
  applyTheme(initialTheme)
  
  // 移除 no-transition 类以恢复过渡效果
  setTimeout(() => {
    html.classList.remove('no-transition')
  }, 0)
}

export function getTheme() {
  return globalTheme.value
}

export function setGlobalTheme(theme) {
  setTheme(theme)
}
