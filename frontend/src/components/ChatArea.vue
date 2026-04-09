<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { NInput, NButton, NScrollbar } from 'naive-ui'
import { useSessionStore } from '../stores/sessionStore'
import { assistantMarkdownToHtml } from '../utils/markdown'

const sessionStore = useSessionStore()
const inputValue = ref('')
const messagesContainer = ref(null)

// 滚动到底部
function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTo({ top: messagesContainer.value.scrollHeight, behavior: 'smooth' })
    }
  })
}

watch(() => sessionStore.messages.length, scrollToBottom)
watch(() => sessionStore.isStreaming, (streaming) => {
  if (streaming) scrollToBottom()
})

async function handleSend() {
  if (!inputValue.value.trim()) return
  const content = inputValue.value
  inputValue.value = ''
  await sessionStore.sendMessage(content)
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

function formatTime(isoString) {
  if (!isoString) return ''
  return new Date(isoString).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function renderAssistant(msg) {
  return assistantMarkdownToHtml(msg.content)
}

const showStreamingPlaceholder = computed(() => {
  if (!sessionStore.isStreaming) return false
  const list = sessionStore.messages
  const last = list[list.length - 1]
  return !last || last.role !== 'assistant'
})

onMounted(() => {
  sessionStore.connectWebSocket()
})

onUnmounted(() => {
  sessionStore.disconnectWebSocket()
})
</script>

<template>
  <div class="h-full flex flex-col">
    <!-- 消息列表 -->
    <n-scrollbar ref="messagesContainer" class="flex-1 p-4">
      <!-- 空状态 -->
      <div v-if="sessionStore.messages.length === 0" class="h-full flex items-center justify-center text-gray-400">
        <div class="text-center">
          <div class="text-4xl mb-4">💬</div>
          <div>开始对话吧！</div>
          <div class="text-sm mt-2">选择模式、上传文件后发送消息</div>
        </div>
      </div>

      <!-- 消息列表 -->
      <div v-else class="space-y-4">
        <div
          v-for="msg in sessionStore.messages"
          :key="msg.id"
          :class="[
            'flex',
            msg.role === 'user' ? 'justify-end' : 'justify-start'
          ]"
        >
          <div
            :class="[
              'max-w-2xl rounded-lg px-4 py-2',
              msg.role === 'user'
                ? 'bg-green-600 text-white'
                : 'bg-gray-100 text-gray-800'
            ]"
          >
            <!-- 消息内容：用户纯文本，助手 Markdown → HTML -->
            <div
              v-if="msg.role === 'user'"
              class="whitespace-pre-wrap break-words"
            >{{ msg.content }}</div>
            <div
              v-else
              class="assistant-md break-words text-left"
              v-html="renderAssistant(msg)"
            />

            <!-- 时间戳 -->
            <div
              :class="[
                'text-xs mt-1',
                msg.role === 'user' ? 'text-green-100' : 'text-gray-400'
              ]"
            >
              {{ formatTime(msg.created_at) }}
            </div>
          </div>
        </div>

        <!-- 正在输入指示器 -->
        <div v-if="showStreamingPlaceholder" class="flex justify-start">
          <div class="bg-gray-100 rounded-lg px-4 py-2 text-gray-500">
            <span class="animate-pulse">正在输入...</span>
          </div>
        </div>
      </div>
    </n-scrollbar>

    <!-- 输入区域 -->
    <div class="border-t bg-white p-4">
      <div class="flex gap-2">
        <n-input
          v-model:value="inputValue"
          type="textarea"
          :rows="2"
          placeholder="输入消息... (Enter 发送，Shift+Enter 换行)"
          @keydown="handleKeydown"
        />
        <n-button
          type="primary"
          :disabled="!inputValue.trim()"
          :loading="sessionStore.isStreaming"
          @click="handleSend"
        >
          发送
        </n-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.assistant-md :deep(p) {
  margin: 0.35em 0;
}
.assistant-md :deep(p:first-child) {
  margin-top: 0;
}
.assistant-md :deep(p:last-child) {
  margin-bottom: 0;
}
.assistant-md :deep(ul),
.assistant-md :deep(ol) {
  margin: 0.35em 0;
  padding-left: 1.25rem;
}
.assistant-md :deep(ul) {
  list-style-type: disc;
}
.assistant-md :deep(ol) {
  list-style-type: decimal;
}
.assistant-md :deep(pre) {
  margin: 0.5em 0;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.06);
  overflow-x: auto;
  font-size: 0.875em;
}
.assistant-md :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.9em;
}
.assistant-md :deep(p code),
.assistant-md :deep(li code) {
  padding: 0.1em 0.35em;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.08);
}
.assistant-md :deep(a) {
  color: #15803d;
  text-decoration: underline;
}
.assistant-md :deep(strong) {
  font-weight: 600;
}
</style>
