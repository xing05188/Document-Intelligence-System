<script setup>
import { NConfigProvider, NMessageProvider, NDialogProvider } from 'naive-ui'
import { computed } from 'vue'
import Sidebar from './components/Sidebar.vue'
import ChatArea from './components/ChatArea.vue'
import ModeSelector from './components/ModeSelector.vue'
import FilePanel from './components/FilePanel.vue'
import { useSessionStore } from './stores/sessionStore'

const sessionStore = useSessionStore()
sessionStore.init()

const themeOverrides = {
  common: {
    primaryColor: '#18a058',
    primaryColorHover: '#36ad6a',
  }
}
</script>

<template>
  <n-config-provider :theme-overrides="themeOverrides">
    <n-message-provider>
      <n-dialog-provider>
        <div class="h-screen flex">
          <!-- 侧边栏 -->
          <aside class="w-64 border-r bg-gray-50 flex flex-col">
            <div class="p-4 border-b">
              <h1 class="text-lg font-bold text-gray-700">文档智能系统</h1>
            </div>
            <Sidebar />
          </aside>

          <!-- 主内容区 -->
          <main class="flex-1 flex flex-col">
            <!-- 模式选择器 -->
            <div class="border-b bg-white px-4 py-3">
              <ModeSelector />
            </div>

            <!-- 文件面板 -->
            <div class="border-b bg-gray-50 px-4 py-3 max-h-48 overflow-y-auto">
              <FilePanel />
            </div>

            <!-- 聊天区域 -->
            <div class="flex-1 overflow-hidden">
              <ChatArea />
            </div>
          </main>
        </div>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>
