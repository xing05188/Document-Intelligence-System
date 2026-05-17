<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { useTabStore } from './stores/tabStore'
import { useAuthStore } from './stores/authStore'
import { useSessionStore } from './stores/sessionStore'
import { useTheme } from './composables/useTheme'
import AuthPanel from './components/AuthPanel.vue'
import AppSidebar from './components/AppSidebar.vue'
import LibraryView from './components/library/LibraryView.vue'
import ChatView from './components/chat/ChatView.vue'
import WorkflowView from './components/workflow/WorkflowView.vue'
import BatchModal from './components/BatchModal.vue'

const tabStore = useTabStore()
const authStore = useAuthStore()
const sessionStore = useSessionStore()
const { theme } = useTheme()
const showBatchModal = ref(false)

// 计算主题属性，自动应用到根元素
const appTheme = computed(() => theme.value || 'light')

// 挂载时初始化认证状态
onMounted(() => {
  authStore.init()
})

// 当用户登录成功后，初始化会话
watch(() => authStore.isAuthenticated, (isAuth) => {
  if (isAuth) {
    sessionStore.init()
  }
}, { immediate: true })

function openBatchModal() {
  showBatchModal.value = true
}

function closeBatchModal() {
  showBatchModal.value = false
}
</script>

<template>
  <div class="app" :data-theme="appTheme">
    <!-- 未登录显示登录界面 -->
    <AuthPanel v-if="!authStore.isAuthenticated && !authStore.isInitializing" />

    <!-- 已登录显示主界面 -->
    <template v-else-if="authStore.isAuthenticated">
      <div class="app-layout">
        <!-- 左侧边栏 -->
        <AppSidebar />

        <!-- 右侧主内容区 -->

      <main class="main-content">
        <LibraryView v-if="tabStore.currentTab === 'library'" />
        <!-- keep-alive：避免每次从文档库切回时整页销毁/重建 ChatView（WebSocket 重连 + 全量 Markdown 重算导致卡顿） -->
        <keep-alive>
          <ChatView v-if="tabStore.currentTab === 'chat'" />
        </keep-alive>
        <WorkflowView
          v-if="tabStore.currentTab === 'workflow'"
          @open-batch-modal="openBatchModal"
        />
      </main>
  <!-- 批量模态框 -->

      <BatchModal
        :visible="showBatchModal"
        @close="closeBatchModal"
          />
          </div>
    </template>

    <!-- 初始化中显示加载状态 -->
    <div v-else class="loading-screen">
      <div class="loading-spinner"></div>
      <p>加载中...</p>
    </div>
  </div>
</template>
