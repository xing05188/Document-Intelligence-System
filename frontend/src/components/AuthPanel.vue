<script setup>
import { ref, computed } from 'vue'
import { useAuthStore } from '../stores/authStore'
import SvgIcon from './icons/SvgIcon.vue'

const authStore = useAuthStore()

const activeTab = ref('login')
const loading = ref(false)
const errorText = ref('')

// 登录表单
const loginPhone = ref('')
const loginPassword = ref('')

// 注册表单
const registerPhone = ref('')
const registerPassword = ref('')
const registerDisplayName = ref('')

const canLogin = computed(() => loginPhone.value.trim() && loginPassword.value)
const canRegister = computed(() => registerPhone.value.trim() && registerPassword.value.length >= 6)

async function handleLogin() {
  if (!canLogin.value) return
  loading.value = true
  errorText.value = ''
  try {
    await authStore.login(loginPhone.value.trim(), loginPassword.value)
  } catch (e) {
    errorText.value = e?.message || '登录失败'
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  if (!canRegister.value) return
  loading.value = true
  errorText.value = ''
  try {
    await authStore.register(
      registerPhone.value.trim(),
      registerPassword.value,
      registerDisplayName.value.trim() || null
    )
  } catch (e) {
    errorText.value = e?.message || '注册失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-shell">
    <!-- 背景装饰 -->
    <div class="auth-bg-gradient"></div>
    <div class="auth-particles">
      <div class="particle particle-1"></div>
      <div class="particle particle-2"></div>
      <div class="particle particle-3"></div>
      <div class="particle particle-4"></div>
    </div>

    <!-- 登录/注册容器 -->
    <div class="auth-container">
      <!-- 登录界面 -->
      <div v-if="activeTab === 'login'" class="auth-panel login-panel">
        <!-- 左侧：表单 -->
        <div class="auth-side auth-form-side">
          <!-- Logo区域 -->
          <div class="auth-header">
            <div class="auth-logo">
              <div class="auth-logo-icon"><SvgIcon name="document" :size="32" /></div>
              <div class="auth-logo-glow"></div>
            </div>
            <h1 class="auth-title">欢迎回来</h1>
            <p class="auth-subtitle">登录到文档智能系统</p>
          </div>

          <!-- 错误提示 -->
          <div v-if="errorText" class="auth-error">
            <span class="auth-error-icon"><SvgIcon name="warning" :size="16" /></span>
            <span>{{ errorText }}</span>
          </div>

          <!-- 登录表单 -->
          <form class="auth-form" @submit.prevent="handleLogin">
            <div class="auth-field">
              <label class="auth-label">手机号</label>
              <input
                v-model="loginPhone"
                type="tel"
                class="auth-input"
                placeholder="请输入手机号码"
                autocomplete="tel"
              />
            </div>

            <div class="auth-field">
              <label class="auth-label">密码</label>
              <input
                v-model="loginPassword"
                type="password"
                class="auth-input"
                placeholder="请输入密码"
                autocomplete="current-password"
              />
            </div>

            <button
              type="submit"
              class="auth-submit"
              :class="{ loading }"
              :disabled="!canLogin || loading"
            >
              <span v-if="!loading">登录</span>
              <span v-else class="auth-spinner"></span>
            </button>
          </form>

          <!-- 底部链接 -->
          <div class="auth-footer">
            <span class="auth-footer-text">没有账号？</span>
            <button type="button" class="auth-link" @click="activeTab = 'register'">
              立即注册
            </button>
          </div>
        </div>

        <!-- 右侧：插画 -->
        <div class="auth-side auth-illustration-side">
          <div class="illustration-container">
            <div class="illustration">
              <!-- 笔记本电脑 -->
              <div class="laptop">
                <div class="laptop-screen"></div>
                <div class="laptop-bottom"></div>
              </div>
              <!-- 图表元素 -->
              <div class="chart-elements">
                <div class="chart-item chart-1"></div>
                <div class="chart-item chart-2"></div>
                <div class="chart-item chart-3"></div>
              </div>
              <!-- 装饰球 -->
              <div class="deco-balls">
                <div class="ball ball-1"></div>
                <div class="ball ball-2"></div>
                <div class="ball ball-3"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 注册界面 -->
      <div v-else class="auth-panel register-panel">
        <!-- 左侧：插画 -->
        <div class="auth-side auth-illustration-side">
          <div class="illustration-container">
            <div class="illustration">
              <!-- 台式电脑屏幕 -->
              <div class="desktop">
                <div class="desktop-screen"></div>
                <div class="desktop-stand"></div>
              </div>
              <!-- UI 元素 -->
              <div class="ui-elements">
                <div class="ui-item ui-1"></div>
                <div class="ui-item ui-2"></div>
                <div class="ui-item ui-3"></div>
              </div>
              <!-- 装饰球 -->
              <div class="deco-balls">
                <div class="ball ball-1"></div>
                <div class="ball ball-2"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- 右侧：表单 -->
        <div class="auth-side auth-form-side">
          <!-- Logo区域 -->
          <div class="auth-header">
            <div class="auth-logo">
              <div class="auth-logo-icon"><SvgIcon name="sparkle" :size="32" /></div>
              <div class="auth-logo-glow"></div>
            </div>
            <h1 class="auth-title">开始探索</h1>
            <p class="auth-subtitle">注册账号开启智能文档之旅</p>
          </div>

          <!-- 错误提示 -->
          <div v-if="errorText" class="auth-error">
            <span class="auth-error-icon"><SvgIcon name="warning" :size="16" /></span>
            <span>{{ errorText }}</span>
          </div>

          <!-- 注册表单 -->
          <form class="auth-form" @submit.prevent="handleRegister">
            <div class="auth-field">
              <label class="auth-label">手机号</label>
              <input
                v-model="registerPhone"
                type="tel"
                class="auth-input"
                placeholder="请输入手机号码"
                autocomplete="tel"
              />
            </div>

            <div class="auth-field">
              <label class="auth-label">昵称</label>
              <input
                v-model="registerDisplayName"
                type="text"
                class="auth-input"
                placeholder="请输入昵称（可选）"
                autocomplete="name"
              />
            </div>

            <div class="auth-field">
              <label class="auth-label">密码</label>
              <input
                v-model="registerPassword"
                type="password"
                class="auth-input"
                placeholder="至少 6 位密码"
                autocomplete="new-password"
              />
            </div>

            <button
              type="submit"
              class="auth-submit"
              :class="{ loading }"
              :disabled="!canRegister || loading"
            >
              <span v-if="!loading">注册账号</span>
              <span v-else class="auth-spinner"></span>
            </button>
          </form>

          <!-- 底部链接 -->
          <div class="auth-footer">
            <span class="auth-footer-text">已有账号？</span>
            <button type="button" class="auth-link" @click="activeTab = 'login'">
              立即登录
            </button>
          </div>
        </div>
      </div>

      <!-- 标签切换（仅在小屏幕显示） -->
      <div class="auth-mobile-tabs">
        <button
          class="auth-mobile-tab"
          :class="{ active: activeTab === 'login' }"
          @click="activeTab = 'login'"
        >
          登录
        </button>
        <button
          class="auth-mobile-tab"
          :class="{ active: activeTab === 'register' }"
          @click="activeTab = 'register'"
        >
          注册
        </button>
      </div>
    </div>
  </div>
</template>
