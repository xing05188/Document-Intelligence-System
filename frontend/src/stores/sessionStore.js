import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import sessionApi from '../api/sessions'
import messageApi from '../api/messages'
import fileApi from '../api/files'
import agentApi from '../api/agents'

export const useSessionStore = defineStore('session', () => {
  // 状态
  const sessions = ref([])
  const currentSessionId = ref(null)
  const messages = ref([])
  const dataFiles = ref([])
  const templateFiles = ref([])
  const modes = ref([])
  const currentMode = ref('default_conversation')
  const isLoading = ref(false)
  const isStreaming = ref(false)
  const ws = ref(null)

  // 计算属性
  const currentSession = computed(() =>
    sessions.value.find(s => s.session_id === currentSessionId.value)
  )

  const selectedDataFiles = computed(() =>
    dataFiles.value.filter(f => f.is_selected)
  )

  const selectedTemplateFiles = computed(() =>
    templateFiles.value.filter(f => f.is_selected)
  )

  // 模式配置
  const modeConfig = {
    'default_conversation': { requiresData: false, requiresTemplate: false },
    'document_understanding': { requiresData: true, requiresTemplate: false },
    'document_editing': { requiresData: true, requiresTemplate: false },
    'entity_extraction': { requiresData: true, requiresTemplate: null },
    'table_filling': { requiresData: true, requiresTemplate: true },
  }

  const currentModeConfig = computed(() => modeConfig[currentMode.value] || modeConfig['default_conversation'])

  // Actions
  async function loadSessions() {
    try {
      const res = await sessionApi.list()
      sessions.value = res.items
    } catch (e) {
      console.error('加载会话列表失败:', e)
    }
  }

  async function createSession() {
    try {
      // 断开旧连接
      disconnectWebSocket()
      const res = await sessionApi.create({ title: '新会话' })
      sessions.value.unshift(res)
      await selectSession(res.session_id)
    } catch (e) {
      console.error('创建会话失败:', e)
    }
  }

  async function selectSession(sessionId) {
    // 断开旧连接
    disconnectWebSocket()
    currentSessionId.value = sessionId
    await loadMessages(sessionId)
    await loadFiles(sessionId)
    // 更新当前模式
    const session = sessions.value.find(s => s.session_id === sessionId)
    if (session) {
      currentMode.value = session.current_mode || 'default_conversation'
    }
    // 连接 WebSocket
    connectWebSocket()
  }

  async function deleteSession(sessionId) {
    try {
      await sessionApi.delete(sessionId)
      sessions.value = sessions.value.filter(s => s.session_id !== sessionId)
      if (currentSessionId.value === sessionId) {
        currentSessionId.value = sessions.value[0]?.session_id || null
        if (currentSessionId.value) {
          await selectSession(currentSessionId.value)
        } else {
          messages.value = []
          dataFiles.value = []
          templateFiles.value = []
        }
      }
    } catch (e) {
      console.error('删除会话失败:', e)
    }
  }

  async function updateSessionTitle(sessionId, title) {
    try {
      const res = await sessionApi.update(sessionId, { title })
      const idx = sessions.value.findIndex(s => s.session_id === sessionId)
      if (idx !== -1) {
        sessions.value[idx] = { ...sessions.value[idx], ...res }
      }
    } catch (e) {
      console.error('更新会话失败:', e)
    }
  }

  async function switchMode(mode) {
    if (currentMode.value === mode) return
    currentMode.value = mode
    if (currentSessionId.value) {
      await sessionApi.update(currentSessionId.value, { current_mode: mode })
    }
  }

  async function loadMessages(sessionId) {
    try {
      const res = await messageApi.list(sessionId)
      messages.value = res
    } catch (e) {
      console.error('加载消息失败:', e)
    }
  }

  async function loadModes() {
    try {
      const res = await agentApi.getCapabilities()
      modes.value = res.modes
    } catch (e) {
      console.error('加载模式失败:', e)
    }
  }

  async function loadFiles(sessionId) {
    try {
      const res = await fileApi.list(sessionId)
      dataFiles.value = res.data_files || []
      templateFiles.value = res.template_files || []
    } catch (e) {
      console.error('加载文件失败:', e)
    }
  }

  async function uploadFile(file, fileType) {
    if (!currentSessionId.value) return
    try {
      const res = await fileApi.upload(currentSessionId.value, file, fileType)
      if (fileType === 'data') {
        dataFiles.value.unshift(res)
      } else {
        templateFiles.value.unshift(res)
      }
    } catch (e) {
      console.error('上传文件失败:', e)
      throw e
    }
  }

  async function toggleFileSelection(fileId, fileType, isSelected) {
    try {
      await fileApi.updateSelection(currentSessionId.value, [{ file_id: fileId, is_selected: isSelected }])
      const files = fileType === 'data' ? dataFiles.value : templateFiles.value
      const idx = files.findIndex(f => f.id === fileId)
      if (idx !== -1) {
        files[idx].is_selected = isSelected
      }
    } catch (e) {
      console.error('更新文件选择失败:', e)
    }
  }

  async function deleteFile(fileId, fileType) {
    try {
      await fileApi.delete(currentSessionId.value, fileId)
      if (fileType === 'data') {
        dataFiles.value = dataFiles.value.filter(f => f.id !== fileId)
      } else {
        templateFiles.value = templateFiles.value.filter(f => f.id !== fileId)
      }
    } catch (e) {
      console.error('删除文件失败:', e)
    }
  }

  function waitForWebSocketOpen(maxMs = 8000) {
    return new Promise((resolve) => {
      const socket = ws.value
      if (!socket) {
        resolve(false)
        return
      }
      if (socket.readyState === WebSocket.OPEN) {
        resolve(true)
        return
      }
      const start = Date.now()
      const t = setInterval(() => {
        if (!ws.value || ws.value !== socket) {
          clearInterval(t)
          resolve(false)
          return
        }
        if (socket.readyState === WebSocket.OPEN) {
          clearInterval(t)
          resolve(true)
          return
        }
        if (socket.readyState === WebSocket.CLOSED) {
          clearInterval(t)
          resolve(false)
          return
        }
        if (Date.now() - start > maxMs) {
          clearInterval(t)
          resolve(false)
        }
      }, 30)
    })
  }

  // WebSocket 流式聊天
  function connectWebSocket() {
    if (!currentSessionId.value) return
    disconnectWebSocket()

    ws.value = messageApi.connect(currentSessionId.value)

    ws.value.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'start') {
        isStreaming.value = true
      } else if (data.type === 'chunk') {
        // 追加到最后一条助手消息
        const lastMsg = messages.value[messages.value.length - 1]
        if (lastMsg && lastMsg.role === 'assistant') {
          lastMsg.content += data.content
        } else {
          messages.value.push({
            id: Date.now(),
            role: 'assistant',
            content: data.content,
            created_at: new Date().toISOString(),
          })
        }
      } else if (data.type === 'done') {
        isStreaming.value = false
      } else if (data.type === 'error') {
        console.error('流式错误:', data.message)
        isStreaming.value = false
      }
    }

    ws.value.onclose = () => {
      ws.value = null
      isStreaming.value = false
    }

    ws.value.onerror = (e) => {
      console.error('WebSocket 错误:', e)
      ws.value = null
      isStreaming.value = false
    }
  }

  function disconnectWebSocket() {
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
    isStreaming.value = false
  }

  async function sendMessage(content) {
    if (!content.trim()) return

    // 没有会话时自动创建
    if (!currentSessionId.value) {
      await createSession()
    }

    const sessionId = currentSessionId.value

    // 添加用户消息
    messages.value.push({
      id: Date.now(),
      role: 'user',
      content: content.trim(),
      created_at: new Date().toISOString(),
    })

    // 若有 WebSocket，等待连接就绪后走流式
    const canStream = await waitForWebSocketOpen()
    if (ws.value && ws.value.readyState === WebSocket.OPEN && canStream) {
      ws.value.send(JSON.stringify({
        content: content.trim(),
        mode: currentMode.value,
      }))
    } else {
      // 非流式
      isStreaming.value = true
      try {
        await messageApi.send(sessionId, {
          content: content.trim(),
          mode: currentMode.value,
        })
        await loadMessages(sessionId)
      } catch (e) {
        console.error('发送消息失败:', e)
      } finally {
        isStreaming.value = false
      }
    }
  }

  // 初始化
  async function init() {
    await loadSessions()
    await loadModes()
    if (sessions.value.length > 0) {
      await selectSession(sessions.value[0].session_id)
    }
  }

  return {
    // 状态
    sessions,
    currentSessionId,
    messages,
    dataFiles,
    templateFiles,
    modes,
    currentMode,
    isLoading,
    isStreaming,
    // 计算属性
    currentSession,
    selectedDataFiles,
    selectedTemplateFiles,
    currentModeConfig,
    // Actions
    init,
    loadSessions,
    createSession,
    selectSession,
    deleteSession,
    updateSessionTitle,
    switchMode,
    uploadFile,
    toggleFileSelection,
    deleteFile,
    sendMessage,
    connectWebSocket,
    disconnectWebSocket,
  }
})
