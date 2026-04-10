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

function formatFileSize(bytes) {
  if (bytes == null || Number.isNaN(Number(bytes))) return ''
  const n = Number(bytes)
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(2)} KB`
  return `${(n / (1024 * 1024)).toFixed(2)} MB`
}

function fileExtLabel(fileName) {
  if (!fileName || typeof fileName !== 'string') return 'FILE'
  const ext = fileName.split('.').pop()
  return ext ? ext.toUpperCase() : 'FILE'
}

/** 用户消息中与文字一并发送的附件（metadata 与后端一致） */
function userMessageAttachments(msg) {
  const m = msg.metadata || {}
  const data = (m.files || []).map((f) => ({ ...f, _kind: 'data' }))
  const tpl = (m.template_files || []).map((f) => ({ ...f, _kind: 'template' }))
  return [...data, ...tpl]
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
          <!-- 用户：带附件时「文件卡片 + 文案」作为一条消息（与参考图一致） -->
          <div
            v-if="msg.role === 'user' && userMessageAttachments(msg).length > 0"
            class="max-w-md flex flex-col items-end gap-2"
          >
            <div
              v-for="(att, idx) in userMessageAttachments(msg)"
              :key="`${att.file_id ?? idx}-${att.file_name}`"
              class="w-full max-w-sm rounded-lg border border-gray-200 bg-white px-3 py-2.5 shadow-sm"
            >
              <div class="flex items-start gap-3">
                <div
                  class="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-rose-50 text-xs font-bold text-rose-600"
                  aria-hidden="true"
                >
                  {{ fileExtLabel(att.file_name).slice(0, 4) }}
                </div>
                <div class="min-w-0 flex-1">
                  <div class="truncate text-sm font-medium text-gray-900" :title="att.file_name">
                    {{ att.file_name }}
                  </div>
                  <div class="mt-0.5 text-xs text-gray-400">
                    {{ fileExtLabel(att.file_name) }}
                    <span v-if="formatFileSize(att.file_size)"> | {{ formatFileSize(att.file_size) }}</span>
                    <span v-if="att._kind === 'template'" class="ml-1 text-amber-600">· 模板</span>
                  </div>
                </div>
              </div>
            </div>
            <div
              class="rounded-xl bg-amber-50/90 px-4 py-2.5 text-left text-[15px] leading-relaxed text-amber-950 shadow-sm ring-1 ring-amber-100/80"
            >
              <div class="whitespace-pre-wrap break-words">{{ msg.content }}</div>
            </div>
            <div class="text-xs text-gray-400">
              {{ formatTime(msg.created_at) }}
            </div>
          </div>

          <!-- 用户：纯文字（无附件）保持原有绿色气泡 -->
          <div
            v-else-if="msg.role === 'user'"
            class="max-w-2xl rounded-lg bg-green-600 px-4 py-2 text-white"
          >
            <div class="whitespace-pre-wrap break-words">{{ msg.content }}</div>
            <div class="mt-1 text-xs text-green-100">
              {{ formatTime(msg.created_at) }}
            </div>
          </div>

          <!-- 助手 -->
          <div
            v-else
            class="max-w-2xl rounded-lg bg-gray-100 px-4 py-2 text-gray-800"
          >
            <div
              class="assistant-md break-words text-left"
              v-html="renderAssistant(msg)"
            />
            <div class="mt-1 text-xs text-gray-400">
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
