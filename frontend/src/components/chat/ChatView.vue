<script setup>
defineOptions({ name: 'ChatView' })

import { ref, onMounted, onUnmounted, nextTick, watch, computed } from 'vue'
import { marked } from 'marked'
import { useSessionStore } from '../../stores/sessionStore'
import { useFileStore } from '../../stores/fileStore'
import { useLibraryStore } from '../../stores/libraryStore'
import libraryApi from '../../api/library'
import SvgIcon from '../icons/SvgIcon.vue'
import MarkdownRenderer from '../library/MarkdownRenderer.vue'
import JsonRenderer from '../library/JsonRenderer.vue'
import PdfRenderer from '../library/PdfRenderer.vue'
import DocxRenderer from '../library/DocxRenderer.vue'
import ExcelRenderer from '../library/ExcelRenderer.vue'

// 配置 marked
marked.setOptions({
  breaks: true,
  gfm: true,
})

// Markdown 渲染缓存：key = msg.id|index，避免重复解析
const _mdCache = new Map()
const _mdCacheMax = 200
function cachedRenderMarkdown(content, cacheKey) {
  if (!content) return ''
  // 附加内容长度作为 cacheKey 的一部分，使流式追加内容时自动穿透缓存
  const effectiveKey = cacheKey != null ? `${cacheKey}_${content.length}` : null
  if (effectiveKey != null) {
    const cached = _mdCache.get(effectiveKey)
    if (cached !== undefined) return cached
  }
  const html = marked.parse(content)
  if (effectiveKey != null) {
    if (_mdCache.size >= _mdCacheMax) {
      const firstKey = _mdCache.keys().next().value
      _mdCache.delete(firstKey)
    }
    _mdCache.set(effectiveKey, html)
  }
  return html
}

// tableFillPreview 缓存：按消息 id 缓存，避免全量重算
const _tfPreviewCache = new Map()
function getTfPreviewBundle(msg, index) {
  const key = msg.id != null && msg.id !== '' ? String(msg.id) : `_i_${index}`
  const cached = _tfPreviewCache.get(key)
  if (cached !== undefined) return cached
  const b = buildTableFillPreviewBundle(msg)
  _tfPreviewCache.set(key, b)
  return b
}
function clearTfPreviewCache() {
  _tfPreviewCache.clear()
}

const sessionStore = useSessionStore()
const fileStore = useFileStore()
const libraryStore = useLibraryStore()

const messagesContainer = ref(null)
const inputText = ref('')
const textareaRef = ref(null)
const isDragover = ref(false)
const previewEntities = ref({})
const modeToast = ref('')

// 聊天文件预览
const chatPreviewVisible = ref(false)
const chatPreviewFile = ref(null)        // { file_name, id, ... }
const chatPreviewBlob = ref(null)
const chatPreviewLoading = ref(false)
const chatPreviewError = ref('')
const chatPreviewDocType = computed(() => {
  const f = chatPreviewFile.value
  if (!f?.file_name) return 'unknown'
  const ext = f.file_name.split('.').pop().toLowerCase()
  if (ext === 'pdf') return 'pdf'
  if (['docx', 'doc'].includes(ext)) return 'docx'
  if (['xlsx', 'xls'].includes(ext)) return 'excel'
  if (ext === 'md') return 'markdown'
  if (ext === 'json') return 'json'
  if (ext === 'txt') return 'text'
  return 'unknown'
})
const chatPreviewIsText = computed(() => ['markdown', 'text', 'json'].includes(chatPreviewDocType.value))
const chatPreviewTextContent = ref('')

async function openChatFilePreview(att) {
  chatPreviewFile.value = att
  chatPreviewVisible.value = true
  chatPreviewBlob.value = null
  chatPreviewTextContent.value = ''
  chatPreviewError.value = ''
  chatPreviewLoading.value = true

  const sid = sessionStore.currentSessionId
  const fileId = att.id ?? att.file_id
  const ext = (att.file_name || '').split('.').pop().toLowerCase()

  try {
    if (chatPreviewIsText.value) {
      // 文本格式 → 获取文本内容
      if (sid && fileId) {
        const url = `/api/sessions/${encodeURIComponent(sid)}/files/${encodeURIComponent(fileId)}/download`
        const token = localStorage.getItem('access_token') || ''
        const res = await fetch(url, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        })
        if (!res.ok) throw new Error(`下载失败 (${res.status})`)
        const text = await res.text()
        chatPreviewTextContent.value = text
      }
    } else {
      // 二进制格式 → 获取 blob
      if (sid && fileId) {
        const url = `/api/sessions/${encodeURIComponent(sid)}/files/${encodeURIComponent(fileId)}/download`
        const token = localStorage.getItem('access_token') || ''
        const res = await fetch(url, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        })
        if (res.ok) {
          chatPreviewBlob.value = await res.blob()
        } else if (res.status === 404) {
          // 会话文件未找到 → 尝试用 storage_key 或通过文档库下载
          const storageKey = att.storage_key || att.file_path
          if (storageKey) {
            const fallbackUrl = `/api/files/download-by-blob?blob_name=${encodeURIComponent(storageKey)}`
            const res2 = await fetch(fallbackUrl, {
              headers: token ? { Authorization: `Bearer ${token}` } : {},
            })
            if (!res2.ok) throw new Error(`预览加载失败`)
            chatPreviewBlob.value = await res2.blob()
          } else {
            throw new Error('文件未找到')
          }
        } else {
          throw new Error(`下载失败 (${res.status})`)
        }
      }
    }
  } catch (e) {
    chatPreviewError.value = e.message || '预览加载失败'
  } finally {
    chatPreviewLoading.value = false
  }
}

function closeChatPreview() {
  chatPreviewVisible.value = false
  chatPreviewFile.value = null
  chatPreviewBlob.value = null
  chatPreviewTextContent.value = ''
  chatPreviewError.value = ''
}

/** 预览上传区/消息中的非服务器文件（尚未上传到服务端） */
async function previewPendingFile(file) {
  chatPreviewFile.value = file
  chatPreviewVisible.value = true
  chatPreviewBlob.value = null
  chatPreviewTextContent.value = ''
  chatPreviewError.value = ''
  chatPreviewLoading.value = true

  const ext = (file.file_name || '').split('.').pop().toLowerCase()
  const isText = ['md', 'json', 'txt'].includes(ext)

  try {
    if (file.original_file) {
      // 尚未上传的本地文件 → 直接读取
      if (isText) {
        chatPreviewTextContent.value = await file.original_file.text()
      } else {
        chatPreviewBlob.value = file.original_file
      }
    } else if (file.file_url && file.file_url.startsWith('blob:')) {
      // 有 blob URL
      if (isText) {
        const res = await fetch(file.file_url)
        chatPreviewTextContent.value = await res.text()
      } else {
        const res = await fetch(file.file_url)
        chatPreviewBlob.value = await res.blob()
      }
    } else {
      // 来自文档库的文件 → 通过 session download 获取
      return openChatFilePreview(file)
    }
  } catch (e) {
    chatPreviewError.value = e.message || '预览加载失败'
  } finally {
    chatPreviewLoading.value = false
  }
}

let modeToastTimer = null

// 保存生成文件到文档库
const showSaveToLibModal = ref(false)
const saveToLibSpaces = ref([])
const selectedSaveSpaceId = ref('')
const savingFileInfo = ref(null)
const isSavingToLib = ref(false)
const saveToLibMsg = ref('')

async function openSaveToLib(fileInfo) {
  savingFileInfo.value = fileInfo
  saveToLibMsg.value = ''
  selectedSaveSpaceId.value = ''
  try {
    const res = await libraryApi.getSpaces()
    saveToLibSpaces.value = (res?.spaces || []).map(s => ({
      id: s.id,
      name: s.name,
      icon: s.icon || '📁',
    }))
    if (saveToLibSpaces.value.length > 0) {
      selectedSaveSpaceId.value = saveToLibSpaces.value[0].id
    }
    showSaveToLibModal.value = true
  } catch (e) {
    saveToLibMsg.value = '加载文档空间失败: ' + (e.message || '')
  }
}

async function confirmSaveToLib() {
  if (!selectedSaveSpaceId.value || !savingFileInfo.value) return
  isSavingToLib.value = true
  saveToLibMsg.value = ''
  try {
    await libraryApi.saveGeneratedFile(selectedSaveSpaceId.value, {
      file_path: savingFileInfo.value.file_path,
      file_name: savingFileInfo.value.file_name,
    })
    saveToLibMsg.value = '✓ 已保存到文档库'
    setTimeout(() => { showSaveToLibModal.value = false }, 1200)
  } catch (e) {
    saveToLibMsg.value = '保存失败: ' + (e.response?.data?.detail || e.message || '')
  } finally {
    isSavingToLib.value = false
  }
}

// 文档库导入弹窗
const showLibraryModal = ref(false)
const libSpaces = ref([])
const selectedLibSpaceId = ref('')
const libDocs = ref([])
const loadingLibDocs = ref(false)
const selectedLibDocIds = ref(new Set())

const showProgress = computed(() => sessionStore.showProgressBar)
const progressVal = computed(() => sessionStore.progressValue)
const progressMsg = computed(() => sessionStore.progressMessage)
const pendingAttachments = computed(() => ([
  ...fileStore.tempFiles.data.map(file => ({ ...file, _kind: 'data' })),
  ...fileStore.tempFiles.template.map(file => ({ ...file, _kind: 'template' }))
]))

const chatModes = ['default_conversation', 'document_understanding', 'document_editing', 'mixed']
const modeLabels = {
  default_conversation: '默认对话',
  document_understanding: '文档理解',
  document_editing: '文档编辑',
  mixed: '提取与填表'
}

async function switchChatMode(mode) {
  if (sessionStore.currentMode === mode) return
  await sessionStore.switchMode(mode)
  modeToast.value = `已切换至「${modeLabels[mode] || mode}」模式`
  if (modeToastTimer) clearTimeout(modeToastTimer)
  modeToastTimer = setTimeout(() => {
    modeToast.value = ''
    modeToastTimer = null
  }, 1800)
}

const quickActions = [
  { icon: 'document', text: '分析文档', prompt: '分析这份文档的核心内容' },
  { icon: 'target', text: '提取信息', prompt: '提取文档中的关键信息' },
  { icon: 'translate', text: '翻译内容', prompt: '帮我翻译这篇论文' },
  { icon: 'workflow', text: '使用工作流', action: 'workflow' }
]

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

watch(() => sessionStore.currentSessionId, () => {
  // 切换会话时清空渲染缓存
  _mdCache.clear()
  _tfPreviewCache.clear()
  scrollToBottom()
})

watch(() => sessionStore.messages.length, () => {
  scrollToBottom()
})

watch(() => sessionStore.isStreaming, (streaming) => {
  if (streaming) scrollToBottom()
})

onMounted(() => {
  sessionStore.connectSSE()
  scrollToBottom()
})

onUnmounted(() => {
  sessionStore.disconnectSSE()
  if (modeToastTimer) clearTimeout(modeToastTimer)
})

function insertPrompt(prompt) {
  if (prompt.action) {
    const tabStore = window.__tabStore__
    if (tabStore) tabStore.switchTab(prompt.action)
  }
}

function formatTime(isoString) {
  if (!isoString) return ''
  const dt = new Date(isoString)
  if (Number.isNaN(dt.getTime())) return ''
  return dt.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function copyMessage(content) {
  navigator.clipboard.writeText(content)
}

function autoResize() {
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto'
    textareaRef.value.style.height = Math.min(textareaRef.value.scrollHeight, 200) + 'px'
  }
}

function handleKeyDown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text) return

  await sessionStore.sendMessage(text, sessionStore.currentMode)
  inputText.value = ''
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto'
  }
}

function handleDragOver(e) {
  e.preventDefault()
  isDragover.value = true
}

function handleDragLeave() {
  isDragover.value = false
}

function handleDrop(e) {
  e.preventDefault()
  isDragover.value = false
  const files = Array.from(e.dataTransfer.files)
  if (files.length > 0) {
    files.forEach(file => fileStore.addFile(fileStore.currentFileType, file))
  }
}

function handleFileInput(e) {
  const files = Array.from(e.target.files)
  if (files.length > 0) {
    files.forEach(file => fileStore.addFile(fileStore.currentFileType, file))
  }
}

function triggerFileInput() {
  const input = document.createElement('input')
  input.type = 'file'
  input.multiple = true
  input.accept = '.pdf,.doc,.docx,.xlsx,.xls,.txt,.json'
  input.onchange = handleFileInput
  input.click()
}

function switchFileType(type) {
  fileStore.switchFileType(type)
}

// ==================== 从文档库导入 ====================
async function openLibraryModal() {
  showLibraryModal.value = true
  selectedLibSpaceId.value = ''
  libDocs.value = []
  selectedLibDocIds.value = new Set()
  try {
    const res = await libraryApi.getSpaces()
    libSpaces.value = res?.spaces || []
  } catch (e) {
    console.error('加载文档库空间失败:', e)
    libSpaces.value = []
  }
}

async function onLibSpaceChange(spaceId) {
  selectedLibSpaceId.value = spaceId
  selectedLibDocIds.value = new Set()
  if (!spaceId) {
    libDocs.value = []
    return
  }
  loadingLibDocs.value = true
  try {
    await libraryStore.loadDocs(spaceId)
    libDocs.value = [...libraryStore.currentDocs]
  } catch (e) {
    console.error('加载文档失败:', e)
    libDocs.value = []
  } finally {
    loadingLibDocs.value = false
  }
}

function toggleLibDoc(docId) {
  const set = new Set(selectedLibDocIds.value)
  if (set.has(docId)) {
    set.delete(docId)
  } else {
    set.add(docId)
  }
  selectedLibDocIds.value = set
}

function importSelectedDocs() {
  const docs = libDocs.value.filter(d => selectedLibDocIds.value.has(d.id))
  for (const doc of docs) {
    fileStore.addLibraryFile(doc, fileStore.currentFileType)
  }
  showLibraryModal.value = false
}

function closeLibraryModal() {
  showLibraryModal.value = false
}
// ====================

function removeFile(id, type) {
  fileStore.removeFile(id, type)
}

function formatFileSize(bytes) {
  if (!bytes) return ''
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function getFileExt(fileName) {
  if (!fileName || typeof fileName !== 'string') return 'FILE'
  const ext = fileName.split('.').pop()
  return ext ? ext.toUpperCase() : 'FILE'
}

function downloadResultFile(fileInfo) {
  const sid = sessionStore.currentSessionId
  if (fileInfo?.file_id && sid) {
    const url = `/api/sessions/${encodeURIComponent(sid)}/files/${encodeURIComponent(fileInfo.file_id)}/download`
    window.open(url, '_blank', 'noopener,noreferrer')
    return
  }
  if (!fileInfo?.file_path) return
  const url = `/api/files/download?path=${encodeURIComponent(fileInfo.file_path)}`
  const a = document.createElement('a')
  a.href = url
  a.download = fileInfo.file_name
  a.click()
}

/** 预览生成的文件 */
function previewGeneratedFile(fileInfo) {
  openChatFilePreview({
    id: fileInfo.file_id,
    file_id: fileInfo.file_id,
    file_name: fileInfo.file_name,
    file_size: fileInfo.file_size,
    storage_key: fileInfo.storage_key || fileInfo.file_path,
    file_path: fileInfo.file_path,
  })
}

// ============ 实体提取表格预览 ============
function getPreviewEntities(msg) {
  if (!msg) return []
  if (previewEntities.value[msg.id]) return previewEntities.value[msg.id]
  const entities = msg.entitiesData || []
  if (entities.length > 0) {
    previewEntities.value[msg.id] = entities
  }
  return entities
}

function getEntityHeaders(msg) {
  const entities = getPreviewEntities(msg)
  if (!entities || entities.length === 0) return []
  return Object.keys(entities[0])
}

function getEntityCells(entity, header) {
  const val = entity[header]
  if (val === undefined || val === null) return ''
  if (Array.isArray(val)) return val[0] ?? ''
  return String(val)
}

function downloadEntitiesJson(msg) {
  const entities = getPreviewEntities(msg)
  if (!entities.length) return
  const json = JSON.stringify(entities, null, 2)
  const blob = new Blob([json], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'extraction_result.json'
  a.click()
  URL.revokeObjectURL(url)
}

/** WebSocket 写在根上；历史消息可能在 metadata.tableFillingData */
function getTableFillingData(msg) {
  if (!msg || msg.role !== 'assistant') return null
  let metadata = msg.metadata
  if (typeof metadata === 'string') {
    try {
      metadata = JSON.parse(metadata)
    } catch {
      metadata = null
    }
  }
  return msg.tableFillingData ?? metadata?.tableFillingData ?? metadata?.table_filling_data ?? null
}

function getTableFillDownloadFiles(msg) {
  const tf = getTableFillingData(msg)
  if (Array.isArray(tf?.generated_files) && tf.generated_files.length) return tf.generated_files
  if (Array.isArray(tf?.generatedFiles) && tf.generatedFiles.length) return tf.generatedFiles
  if (Array.isArray(msg?.generated_files) && msg.generated_files.length) return msg.generated_files
  if (Array.isArray(msg?.generatedFiles) && msg.generatedFiles.length) return msg.generatedFiles
  const fallback = []
  const templateOutput = tf?.template_output || tf?.output_template
  if (templateOutput) {
    const path = String(templateOutput)
    const suffix = path.split(/[\\/]/).pop()?.split('.').pop() || 'docx'
    fallback.push({
      file_path: path,
      file_name: path.split(/[\\/]/).pop() || `table_filling_result.${suffix}`,
    })
  }
  if (tf?.output_json) {
    const path = String(tf.output_json)
    fallback.push({
      file_path: path,
      file_name: path.split(/[\\/]/).pop() || 'table_filling_result.json',
    })
  }
  if (fallback.length) return fallback
  return []
}

const TABLE_PREVIEW_MAX_ROWS = 50

function tablePreviewRows(tf) {
  if (!tf || typeof tf !== 'object') return []
  const a = tf.previewData
  const b = tf.filtered_rows
  if (Array.isArray(a) && a.length) return a
  if (Array.isArray(b) && b.length) return b
  return []
}

function tablePreviewDisplayRows(tf) {
  return tablePreviewRows(tf).slice(0, TABLE_PREVIEW_MAX_ROWS)
}

function tablePreviewExtraCount(tf) {
  const n = tablePreviewRows(tf).length
  return n > TABLE_PREVIEW_MAX_ROWS ? n - TABLE_PREVIEW_MAX_ROWS : 0
}

function tablePreviewColumns(rows) {
  if (!Array.isArray(rows) || rows.length === 0) return []
  const ordered = []
  const seen = new Set()
  const first = rows[0]
  if (first && typeof first === 'object' && !Array.isArray(first)) {
    for (const k of Object.keys(first)) {
      ordered.push(k)
      seen.add(k)
    }
  }
  for (const row of rows) {
    if (!row || typeof row !== 'object' || Array.isArray(row)) continue
    for (const k of Object.keys(row)) {
      if (!seen.has(k)) {
        seen.add(k)
        ordered.push(k)
      }
    }
  }
  return ordered
}

function formatTablePreviewCell(val) {
  if (val === null || val === undefined || val === '') return '—'
  if (typeof val === 'object') {
    try {
      return JSON.stringify(val)
    } catch {
      return String(val)
    }
  }
  return String(val)
}

/** 每条助手消息最多算一次预览结构，避免模板里对每格重复 tablePreviewColumns */
function buildTableFillPreviewBundle(msg) {
  const tf = getTableFillingData(msg)
  if (!tf || tf.success === undefined) return null
  const rows = tablePreviewRows(tf)
  if (!rows.length) return null
  const columns = tablePreviewColumns(rows)
  const displayRows = rows.slice(0, TABLE_PREVIEW_MAX_ROWS)
  const extra = Math.max(0, rows.length - TABLE_PREVIEW_MAX_ROWS)
  return { tf, columns, displayRows, totalRows: rows.length, extra }
}

function tablePreviewBundleFor(msg, index) {
  return getTfPreviewBundle(msg, index)
}

function tablePreviewBundleList(msg, index) {
  const b = getTfPreviewBundle(msg, index)
  return b ? [b] : []
}

function getFileStyle(fileName) {
  const ext = (fileName || '').split('.').pop().toLowerCase()
  const map = {
    pdf:  { bg: 'rgba(239, 68, 68, 0.15)', text: '#ef4444', icon: 'filePdf' },
    doc:  { bg: 'rgba(59, 130, 246, 0.15)', text: '#3b82f6', icon: 'fileDoc' },
    docx: { bg: 'rgba(59, 130, 246, 0.15)', text: '#3b82f6', icon: 'fileDoc' },
    xls:  { bg: 'rgba(16, 185, 129, 0.15)', text: '#10b981', icon: 'fileXls' },
    xlsx: { bg: 'rgba(16, 185, 129, 0.15)', text: '#10b981', icon: 'fileXls' },
    txt:  { bg: 'rgba(161, 161, 170, 0.15)', text: '#a1a1aa', icon: 'fileTxt' },
    md:   { bg: 'rgba(161, 161, 170, 0.15)', text: '#a1a1aa', icon: 'fileTxt' },
    json: { bg: 'rgba(250, 204, 21, 0.15)', text: '#eab308', icon: 'fileTxt' },
  }
  return map[ext] || { bg: 'rgba(161, 161, 170, 0.15)', text: '#a1a1aa', icon: 'file' }
}

function getFileLabel(fileName) {
  const ext = (fileName || '').split('.').pop().toLowerCase()
  const map = {
    pdf: 'PDF', doc: 'DOC', docx: 'DOCX',
    xls: 'XLS', xlsx: 'XLSX',
    txt: 'TXT', md: 'MD', json: 'JSON', csv: 'CSV',
    ppt: 'PPT', pptx: 'PPTX',
  }
  return map[ext] || ext.toUpperCase() || '?'
}

function userMessageAttachments(msg) {
  const m = msg.metadata || {}
  const data = (m.files || []).map((f) => ({ ...f, _kind: 'data' }))
  const tpl = (m.template_files || []).map((f) => ({ ...f, _kind: 'template' }))
  return [...data, ...tpl]
}
</script>

<template>
  <div class="chat-view">
    <div class="chat-main">
      <div v-if="modeToast" class="mode-toast">{{ modeToast }}</div>
      <div class="chat-messages" ref="messagesContainer">
        <div v-if="sessionStore.isInitializing" class="welcome-state">
          <div class="welcome-icon"><SvgIcon name="chat" :size="48" /></div>
          <h1 class="welcome-title">加载中...</h1>
        </div>

        <div v-else-if="sessionStore.messages.length === 0" class="welcome-state">
          <div class="welcome-icon"><SvgIcon name="chat" :size="48" /></div>
          <h1 class="welcome-title">智能对话</h1>
          <p class="welcome-subtitle">
            通过自然语言与系统交互，完成文档分析，信息提取，内容生成等任务
          </p>
          <div class="quick-actions">
            <button
              v-for="action in quickActions"
              :key="action.text"
              class="quick-action"
              @click="insertPrompt(action)"
            >
              <SvgIcon :name="action.icon" :size="18" />
              <span>{{ action.text }}</span>
            </button>
          </div>
        </div>

        <div
          v-for="(msg, index) in sessionStore.messages"
          :key="msg.id != null ? msg.id : `m-${index}`"
          class="message"
          :class="msg.role"
        >
          <div class="message-avatar">
            <SvgIcon v-if="msg.role === 'user'" name="user" :size="20" />
            <SvgIcon v-else-if="msg.role === 'system'" name="info" :size="20" />
            <SvgIcon v-else name="robot" :size="20" />
          </div>
          <div class="message-content">
            <!-- 用户消息：带附件时显示文件卡片 -->
            <template v-if="msg.role === 'user' && userMessageAttachments(msg).length > 0">
              <div class="user-attachments">
                <div
                  v-for="(att, idx) in userMessageAttachments(msg)"
                  :key="`${att.id ?? att.file_id ?? idx}-${att.file_name}`"
                  class="attachment-card"
                  :class="{ 'attachment-uploading': att.pending }"
                >
                  <div
                    class="attachment-icon"
                    :style="{ background: getFileStyle(att.file_name).bg, color: getFileStyle(att.file_name).text }"
                  >
                    <SvgIcon v-if="att.pending" name="clock" :size="20" />
                    <span v-else class="file-type-label-sm">{{ getFileLabel(att.file_name) }}</span>
                  </div>
                  <div class="attachment-info">
                    <div class="attachment-name" :title="att.file_name">{{ att.file_name }}</div>
                    <div class="attachment-meta">
                      <span v-if="att.pending" class="upload-status">上传中...</span>
                      <template v-else>
                        {{ getFileExt(att.file_name) }}
                        <span v-if="formatFileSize(att.file_size)"> | {{ formatFileSize(att.file_size) }}</span>
                      </template>
                      <span v-if="att._kind === 'template'" class="template-badge">· 模板</span>
                    </div>
                  </div>
                  <button
                    v-if="!att.pending"
                    class="attachment-preview-btn"
                    type="button"
                    title="预览"
                    @click.stop="openChatFilePreview(att)"
                  >预览</button>
                </div>
              </div>
              <div v-if="msg.content" class="message-bubble">
                <span>{{ msg.content }}</span>
              </div>
            </template>
            <!-- 用户消息：无附件 -->
            <div v-else-if="msg.role === 'user'" class="message-bubble">
              <span>{{ msg.content }}</span>
            </div>
            <!-- 系统消息 -->
            <div v-else-if="msg.role === 'system'" class="message-bubble system">
              <span>{{ msg.content }}</span>
            </div>
            <!-- 助手消息 -->
            <div v-else class="message-bubble" :class="{ 'md-content': msg.role === 'assistant' }">
              <div v-if="msg.role === 'assistant'" v-html="cachedRenderMarkdown(msg.content, msg.id)"></div>
              <!-- Loading 动画 -->
              <div v-if="msg.isLoading" class="typing-indicator">
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
              </div>
              <!-- 表格填表预览：每条消息只取一次 bundle（computed 预聚合 + 单次 list 迭代） -->
              <template v-for="tb in tablePreviewBundleList(msg, index)" :key="(msg.id != null ? msg.id : index) + '-tbl'">
                <div class="entity-preview table-fill-preview">
                  <div class="entity-preview-header">
                    <div>
                      <span class="entity-preview-title">
                        <SvgIcon name="clipboard" :size="16" /> 表格结果预览（{{ tb.totalRows }} 行）
                      </span>
                      <span v-if="tb.tf.matched_rows != null" class="table-fill-stats table-fill-stats-inline">
                        命中 {{ tb.tf.matched_rows }}/{{ tb.tf.total_rows ?? '—' }} 行
                      </span>
                    </div>
                    <div v-if="getTableFillDownloadFiles(msg).length" class="entity-preview-actions">
                      <button
                        v-for="f in getTableFillDownloadFiles(msg)"
                        :key="'preview-'+f.file_id"
                        class="entity-action-btn"
                        type="button"
                        @click="previewGeneratedFile(f)"
                      >
                        {{ getFileExt(f.file_name) }} 预览
                      </button>
                      <button
                        v-for="f in getTableFillDownloadFiles(msg)"
                        :key="'dl-'+f.file_id"
                        class="entity-action-btn"
                        type="button"
                        @click="downloadResultFile(f)"
                      >
                        ↓ 下载
                      </button>
                    </div>
                  </div>
                  <div class="entity-table-wrapper">
                    <table class="entity-table">
                      <thead>
                        <tr>
                          <th v-for="col in tb.columns" :key="col">
                            {{ col }}
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(row, ri) in tb.displayRows" :key="ri">
                          <td
                            v-for="col in tb.columns"
                            :key="col"
                            :title="formatTablePreviewCell(row && row[col] !== undefined ? row[col] : '')"
                          >
                            {{ formatTablePreviewCell(row && row[col] !== undefined ? row[col] : '') }}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                  <div v-if="tb.extra > 0" class="entity-preview-more">
                    还有 {{ tb.extra }} 行未展示，请下载生成文件查看全部
                  </div>
                </div>
              </template>
              <!-- 仅表格填表：无 previewData 时仍要下载；勿用 getTableFillDownloadFiles 单独判断，否则无 tableFillingData 时会误用 msg.generated_files 与实体提取重复 -->
              <div
                v-if="getTableFillingData(msg) && getTableFillDownloadFiles(msg).length && !tablePreviewBundleFor(msg, index)"
                class="entity-preview table-fill-preview table-fill-downloads-only"
              >
                <div class="entity-preview-header">
                  <span class="entity-preview-title"><SvgIcon name="clipboard" :size="16" /> 生成结果</span>
                  <div class="entity-preview-actions">
                    <button
                      v-for="f in getTableFillDownloadFiles(msg)"
                      :key="'preview-'+f.file_id"
                      class="entity-action-btn"
                      type="button"
                      @click="previewGeneratedFile(f)"
                    >
                      {{ getFileExt(f.file_name) }} 预览
                    </button>
                    <button
                      v-for="f in getTableFillDownloadFiles(msg)"
                      :key="'dl-'+f.file_id"
                      class="entity-action-btn"
                      type="button"
                      @click="downloadResultFile(f)"
                    >
                      ↓ 下载
                    </button>
                  </div>
                </div>
              </div>
              <!-- 混合模式专用：仅展示统一填表后的结果预览与下载 -->
              <template v-if="msg.mixedSource === 'merged' && (msg.tableFillingPreview || msg.generated_files?.length)">
                <div class="entity-preview table-fill-preview">
                  <div class="entity-preview-header">
                    <div>
                      <span class="entity-preview-title"><SvgIcon name="clipboard" :size="16" /> 混合填表结果预览</span>
                      <span v-if="msg.tableFillingPreview?.matched_rows != null" class="table-fill-stats table-fill-stats-inline">
                        共 {{ msg.tableFillingPreview.matched_rows }} 行
                      </span>
                    </div>
                    <div v-if="msg.generated_files?.length" class="entity-preview-actions">
                      <button v-for="f in msg.generated_files" :key="'preview-'+f.file_id" class="entity-action-btn" @click="previewGeneratedFile(f)">
                        {{ getFileExt(f.file_name) }} 预览
                      </button>
                      <button v-for="f in msg.generated_files" :key="'dl-'+f.file_id" class="entity-action-btn" @click="downloadResultFile(f)">
                        ↓ 下载
                      </button>
                    </div>
                  </div>
                  <div v-if="msg.tableFillingPreview?.previewData?.length" class="entity-table-wrapper">
                    <table class="entity-table">
                      <thead>
                        <tr>
                          <th v-for="col in tablePreviewColumns(msg.tableFillingPreview.previewData)" :key="col">{{ col }}</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(row, ri) in msg.tableFillingPreview.previewData.slice(0, 50)" :key="ri">
                          <td v-for="col in tablePreviewColumns(msg.tableFillingPreview.previewData)" :key="col">
                            {{ formatTablePreviewCell(row && row[col] !== undefined ? row[col] : '') }}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                  <div v-else class="entity-preview-more">
                    已生成混合填表文件，请使用下载按钮查看完整结果。
                  </div>
                  <div v-if="(msg.tableFillingPreview?.previewData?.length ?? 0) > 50" class="entity-preview-more">
                    还有 {{ msg.tableFillingPreview.previewData.length - 50 }} 行未展示，请下载生成文件查看全部
                  </div>
                </div>
              </template>
              <!-- 非混合模式的实体提取结果：表格预览 -->
              <div v-else-if="msg.entitiesData?.length && msg.mixedSource !== 'merged'" class="entity-preview table-fill-preview">
                <div class="entity-preview-header">
                  <span class="entity-preview-title"><SvgIcon name="chart" :size="16" /> 提取结果预览（共 {{ msg.entitiesData.length }} 条）</span>
                  <div class="entity-preview-actions">
                    <button v-for="f in msg.generated_files" :key="'preview-'+f.file_id" class="entity-action-btn" @click="previewGeneratedFile(f)">
                      {{ getFileExt(f.file_name) }} 预览
                    </button>
                    <button v-for="f in msg.generated_files" :key="'dl-'+f.file_id" class="entity-action-btn" @click="downloadResultFile(f)">
                      ↓ 下载
                    </button>
                  </div>
                </div>
                <div class="entity-table-wrapper">
                  <table class="entity-table">
                    <thead>
                      <tr>
                        <th v-for="h in getEntityHeaders(msg)" :key="h">{{ h }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(entity, rowIdx) in msg.entitiesData.slice(0, 20)" :key="rowIdx">
                        <td v-for="h in getEntityHeaders(msg)" :key="h" :title="entity[h] != null ? String(entity[h]) : ''">
                          {{ getEntityCells(entity, h) }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-if="msg.entitiesData.length > 20" class="entity-preview-more">
                  还有 {{ msg.entitiesData.length - 20 }} 条数据，下载完整文件查看全部
                </div>
              </div>
              <!-- 非混合模式的表格填表预览 -->
              <div v-if="msg.tableFillingPreview && msg.mixedSource !== 'merged'" class="entity-preview table-fill-preview">
                <div class="entity-preview-header">
                  <div>
                    <span class="entity-preview-title"><SvgIcon name="clipboard" :size="16" /> 表格结果预览（{{ msg.tableFillingPreview.previewData?.length ?? msg.tableFillingPreview.matched_rows ?? 0 }} 行）</span>
                    <span v-if="msg.tableFillingPreview.matched_rows != null" class="table-fill-stats table-fill-stats-inline">
                      命中 {{ msg.tableFillingPreview.matched_rows }}/{{ msg.tableFillingPreview.total_rows ?? '—' }} 行
                    </span>
                  </div>
                </div>
                <div v-if="msg.tableFillingPreview.previewData?.length" class="entity-table-wrapper">
                  <table class="entity-table">
                    <thead>
                      <tr>
                        <th v-for="col in tablePreviewColumns(msg.tableFillingPreview.previewData)" :key="col">{{ col }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(row, ri) in msg.tableFillingPreview.previewData.slice(0, 50)" :key="ri">
                        <td v-for="col in tablePreviewColumns(msg.tableFillingPreview.previewData)" :key="col">
                          {{ formatTablePreviewCell(row && row[col] !== undefined ? row[col] : '') }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-if="(msg.tableFillingPreview.previewData?.length ?? 0) > 50" class="entity-preview-more">
                  还有 {{ msg.tableFillingPreview.previewData.length - 50 }} 行未展示，请下载生成文件查看全部
                </div>
              </div>
              <!-- 混合模式或非表格任务的文件下载：独立显示，不与 entitiesData 块冲突 -->
              <div
                v-if="msg.generated_files?.length && !getTableFillingData(msg) && msg.entitiesData?.length"
                class="entity-preview table-fill-preview table-fill-downloads-only"
              >
                <div class="entity-preview-header">
                  <span class="entity-preview-title"><SvgIcon name="download" :size="16" /> 表格数据下载</span>
                  <div class="entity-preview-actions">
                    <button v-for="f in msg.generated_files" :key="'preview-'+f.file_id" class="entity-action-btn" @click="previewGeneratedFile(f)">
                      {{ getFileExt(f.file_name) }} 预览
                    </button>
                    <button v-for="f in msg.generated_files" :key="'dl-'+f.file_id" class="entity-action-btn" @click="downloadResultFile(f)">
                      ↓ 下载
                    </button>
                    <button v-for="f in msg.generated_files" :key="'lib-'+f.file_id" class="entity-action-btn save-to-lib-btn" type="button" @click="openSaveToLib(f)">
                      保存到文档库
                    </button>
                  </div>
                </div>
              </div>
              <!-- 仅文件下载：实体提取等场景；表格填表已在上方标题栏处理，勿与 msg.generated_files 再渲一排 -->
              <div
                v-else-if="msg.generated_files?.length && !getTableFillingData(msg)"
                class="entity-preview table-fill-preview table-fill-downloads-only"
              >
                <div class="entity-preview-header">
                  <span class="entity-preview-title"><SvgIcon name="chart" :size="16" /> 生成结果</span>
                  <div class="entity-preview-actions">
                    <button v-for="f in msg.generated_files" :key="f.file_id" class="entity-action-btn" @click="previewGeneratedFile(f)">
                      {{ getFileExt(f.file_name) }} 预览
                    </button>
                    <button v-for="f in msg.generated_files" :key="'dl-'+f.file_id" class="entity-action-btn" @click="downloadResultFile(f)">
                      ↓ 下载
                    </button>
                    <button v-for="f in msg.generated_files" :key="'lib-'+f.file_id" class="entity-action-btn save-to-lib-btn" type="button" @click="openSaveToLib(f)">
                      保存到文档库
                    </button>
                  </div>
                </div>
              </div>
            </div>
            <div class="message-time">{{ formatTime(msg.created_at) }}</div>
          </div>
        </div>

        <!-- 上传文件进度 -->
        <div v-if="sessionStore.isUploadingFiles" class="message system">
          <div class="message-avatar"><SvgIcon name="clock" :size="20" /></div>
          <div class="message-content">
            <div class="message-bubble upload-progress">
              <SvgIcon name="upload" :size="18" />
              <span class="upload-text">{{ sessionStore.uploadProgress || '正在上传文件...' }}</span>
            </div>
          </div>
        </div>

        <!-- 进度条（实体提取/表格填表） -->
        <div v-if="showProgress && (sessionStore.currentMode === 'entity_extraction' || sessionStore.currentMode === 'table_filling' || sessionStore.currentMode === 'mixed')" class="message assistant">
          <div class="message-avatar"><SvgIcon name="gear" :size="20" /></div>
          <div class="message-content">
            <div class="progress-card">
              <div class="progress-header">
                <span class="progress-title">任务处理中</span>
                <span class="progress-msg">{{ progressMsg }}</span>
                <span v-if="progressVal < 100" class="progress-indicator">●</span>
                <span v-else class="progress-done">完成</span>
              </div>
              <div class="progress-bar-container">
                <div class="progress-bar" :style="{ width: progressVal + '%' }"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 保存到文档库弹窗 -->
      <Teleport to="body">
        <div v-if="showSaveToLibModal" class="save-lib-overlay" @click.self="showSaveToLibModal = false">
          <div class="save-lib-modal">
            <div class="save-lib-header">
              <span>保存到文档库</span>
              <button class="save-lib-close" type="button" @click="showSaveToLibModal = false">×</button>
            </div>
            <div class="save-lib-body">
              <div class="save-lib-file-info">
                <span class="save-lib-label">文件：</span>
                <span class="save-lib-filename">{{ savingFileInfo?.file_name }}</span>
              </div>
              <div class="save-lib-space-select">
                <span class="save-lib-label">目标空间：</span>
                <select v-model="selectedSaveSpaceId" class="save-lib-select">
                  <option v-for="s in saveToLibSpaces" :key="s.id" :value="s.id">
                    {{ s.icon }} {{ s.name }}
                  </option>
                </select>
              </div>
              <div v-if="saveToLibSpaces.length === 0 && !saveToLibMsg" class="save-lib-empty">
                暂无文档空间，请先在文档库中创建
              </div>
              <div v-if="saveToLibMsg" class="save-lib-msg" :class="{ success: saveToLibMsg.startsWith('✓') }">
                {{ saveToLibMsg }}
              </div>
            </div>
            <div class="save-lib-footer">
              <button class="save-lib-cancel" type="button" @click="showSaveToLibModal = false">取消</button>
              <button
                class="save-lib-confirm"
                type="button"
                :disabled="!selectedSaveSpaceId || isSavingToLib"
                @click="confirmSaveToLib"
              >
                {{ isSavingToLib ? '保存中...' : '确认保存' }}
              </button>
            </div>
          </div>
        </div>
      </Teleport>

      <div class="chat-input-area">
        <div
          v-if="pendingAttachments.length"
          class="pending-attachments"
        >
          <div
            v-for="file in pendingAttachments"
            :key="file.id"
            class="pending-attachment-card"
            :class="{ unselected: !file.is_selected }"
          >
            <input
              type="checkbox"
              class="pending-attachment-checkbox"
              :checked="file.is_selected"
              @change="fileStore.toggleFileSelection(file.id, file._kind, $event.target.checked)"
            />
            <div
              class="pending-attachment-icon"
              :style="{ background: getFileStyle(file.file_name).bg, color: getFileStyle(file.file_name).text }"
            >
              <span class="file-type-label">{{ getFileLabel(file.file_name) }}</span>
            </div>
            <div class="pending-attachment-body">
              <div class="pending-attachment-name" :title="file.file_name">{{ file.file_name }}</div>
              <div class="pending-attachment-meta">
                {{ getFileExt(file.file_name) }}
                <span v-if="formatFileSize(file.file_size)">{{ formatFileSize(file.file_size) }}</span>
                <span v-if="file._kind === 'template'" class="pending-attachment-kind">模板</span>
              </div>
            </div>
            <button
              class="pending-attachment-preview-btn"
              type="button"
              title="预览"
              @click.stop="previewPendingFile(file)"
            >预览</button>
            <button
              class="pending-attachment-remove"
              type="button"
              @click="removeFile(file.id, file._kind)"
            >
              ×
            </button>
          </div>
        </div>

        <div class="chat-input-shell">
          <div class="chat-input" :class="{ dragover: isDragover }">
            <textarea
              ref="textareaRef"
              v-model="inputText"
              rows="1"
              placeholder="给 AI 发送消息"
              @keydown="handleKeyDown"
              @input="autoResize"
              @dragover="handleDragOver"
              @dragleave="handleDragLeave"
              @drop="handleDrop"
            ></textarea>
          </div>

          <div class="chat-input-toolbar">
            <div class="toolbar-left">
              <div class="mode-tabs mode-tabs-inline">
                <button
                  v-for="mode in chatModes"
                  :key="mode"
                  class="mode-tab"
                  :class="{ active: sessionStore.currentMode === mode }"
                  @click="switchChatMode(mode)"
                >
                  {{ modeLabels[mode] }}
                </button>
              </div>
            </div>

            <div class="toolbar-right">
              <div class="file-type-switcher">
                <button
                  class="file-type-btn"
                  :class="{ active: fileStore.currentFileType === 'data' }"
                  data-type="data"
                  @click.stop="switchFileType('data')"
                >
                  数据文件
                </button>
                <button
                  class="file-type-btn"
                  :class="{ active: fileStore.currentFileType === 'template' }"
                  data-type="template"
                  @click.stop="switchFileType('template')"
                >
                  模板文件
                </button>
              </div>

              <button
                class="toolbar-upload-btn"
                type="button"
                @click="triggerFileInput"
              >
                <SvgIcon name="attachment" :size="16" />
                <span>文件上传</span>
              </button>

              <button
                class="toolbar-upload-btn"
                type="button"
                @click="openLibraryModal"
              >
                <SvgIcon name="book" :size="16" />
                <span>从文档库</span>
              </button>

              <div class="file-count-badges" v-if="fileStore.hasFiles">
                <span v-if="fileStore.hasDataFiles" class="file-badge data-badge">
                  <SvgIcon name="dataFile" :size="14" /> {{ fileStore.dataCount }}
                </span>
                <span v-if="fileStore.hasTemplateFiles" class="file-badge template-badge">
                  <SvgIcon name="template" :size="14" /> {{ fileStore.templateCount }}
                </span>
              </div>

              <button
                class="send-btn"
                :class="{ loading: sessionStore.isStreaming }"
                @click="sendMessage"
                :disabled="!inputText.trim() || sessionStore.isStreaming"
              >
                <SvgIcon v-if="!sessionStore.isStreaming" name="send" :size="18" />
                <span v-else class="send-spinner"></span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 文档库导入弹窗 -->
  <Teleport to="body">
    <div v-if="showLibraryModal" class="lib-import-overlay" @click.self="closeLibraryModal">
      <div class="lib-import-modal">
        <div class="lib-import-header">
          <h3>从文档库导入</h3>
          <button class="lib-import-close" @click="closeLibraryModal">×</button>
        </div>
        <div class="lib-import-body">
          <!-- 空间选择 -->
          <div class="lib-import-section">
            <label class="lib-import-label">选择文档库</label>
            <select
              class="lib-import-select"
              :value="selectedLibSpaceId"
              @change="onLibSpaceChange($event.target.value)"
            >
              <option value="">-- 请选择 --</option>
              <option v-for="sp in libSpaces" :key="sp.id" :value="sp.id">
                {{ sp.name }}
              </option>
            </select>
          </div>

          <!-- 文档列表 -->
          <div v-if="selectedLibSpaceId" class="lib-import-section">
            <label class="lib-import-label">选择文档</label>
            <div v-if="loadingLibDocs" class="lib-import-loading">加载中...</div>
            <div v-else-if="libDocs.length === 0" class="lib-import-empty">该文档库暂无文档</div>
            <div v-else class="lib-import-docs">
              <div
                v-for="doc in libDocs"
                :key="doc.id"
                class="lib-import-doc-item"
                :class="{ selected: selectedLibDocIds.has(doc.id) }"
                @click="toggleLibDoc(doc.id)"
              >
                <span class="lib-import-check">
                  <span v-if="selectedLibDocIds.has(doc.id)">✓</span>
                </span>
                <span class="lib-import-doc-icon"><SvgIcon name="file" :size="16" /></span>
                <span class="lib-import-doc-name">{{ doc.name }}</span>
                <span class="lib-import-doc-size">{{ doc.size }}</span>
              </div>
            </div>
          </div>
        </div>
        <div class="lib-import-footer">
          <button class="lib-import-btn cancel" @click="closeLibraryModal">取消</button>
          <button
            class="lib-import-btn confirm"
            :disabled="selectedLibDocIds.size === 0"
            @click="importSelectedDocs"
          >
            确认导入 ({{ selectedLibDocIds.size }})
          </button>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- 聊天文件预览弹窗 -->
  <Teleport to="body">
    <div
      v-if="chatPreviewVisible"
      class="chat-preview-overlay"
      @click.self="closeChatPreview"
    >
      <div class="chat-preview-modal">
        <!-- Header -->
        <div class="chat-preview-header">
          <span class="chat-preview-title">{{ chatPreviewFile?.file_name || '' }}</span>
          <button class="chat-preview-close" type="button" @click="closeChatPreview">×</button>
        </div>

        <!-- Body -->
        <div class="chat-preview-body">
          <!-- Loading -->
          <div v-if="chatPreviewLoading" class="chat-preview-loading">
            <div class="loading-spinner"></div>
            <span>正在加载...</span>
          </div>

          <!-- Error -->
          <div v-else-if="chatPreviewError" class="chat-preview-error">
            {{ chatPreviewError }}
          </div>

          <!-- Markdown -->
          <div v-else-if="chatPreviewDocType === 'markdown' && chatPreviewTextContent" class="chat-preview-renderer">
            <MarkdownRenderer :content="chatPreviewTextContent" />
          </div>

          <!-- JSON -->
          <div v-else-if="chatPreviewDocType === 'json' && chatPreviewTextContent" class="chat-preview-renderer">
            <JsonRenderer :content="chatPreviewTextContent" />
          </div>

          <!-- Text -->
          <div v-else-if="chatPreviewDocType === 'text' && chatPreviewTextContent" class="chat-preview-text">
            <pre>{{ chatPreviewTextContent }}</pre>
          </div>

          <!-- PDF -->
          <div v-else-if="chatPreviewDocType === 'pdf' && chatPreviewBlob" class="chat-preview-renderer">
            <PdfRenderer :blob="chatPreviewBlob" />
          </div>

          <!-- DOCX -->
          <div v-else-if="chatPreviewDocType === 'docx' && chatPreviewBlob" class="chat-preview-renderer">
            <DocxRenderer :blob="chatPreviewBlob" />
          </div>

          <!-- Excel -->
          <div v-else-if="chatPreviewDocType === 'excel' && chatPreviewBlob" class="chat-preview-renderer">
            <ExcelRenderer :blob="chatPreviewBlob" />
          </div>

          <!-- Unknown -->
          <div v-else-if="!chatPreviewLoading && !chatPreviewError" class="chat-preview-empty">
            无法预览此文件
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
/* =============================================================
   ChatView.vue — 全面优化的智能对话界面样式
   Design System: DeepSeek Theme (CSS Variables from theme.css)
   ============================================================= */

/* ---- Layout ---- */
.chat-view {
  display: flex;
  height: 100%;
  width: 100%;
  background: var(--bg-primary);
  overflow: hidden;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 0;
  position: relative;
  background: var(--bg-primary);
}

/* ---- Mode Toast ---- */
.mode-toast {
  position: fixed;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 100;
  background: var(--accent-primary);
  color: var(--text-inverse);
  padding: 8px 20px;
  border-radius: var(--radius-full);
  font-size: 13px;
  font-weight: 500;
  box-shadow: 0 4px 16px rgba(22, 119, 255, 0.3);
  animation: toast-in 0.3s ease;
  pointer-events: none;
}

@keyframes toast-in {
  from { opacity: 0; transform: translateX(-50%) translateY(-8px); }
  to   { opacity: 1; transform: translateX(-50%) translateY(0); }
}

/* ---- Welcome / Empty State ---- */
.welcome-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
  animation: welcome-fade-in 0.6s ease;
}

@keyframes welcome-fade-in {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}

.welcome-icon {
  width: 80px;
  height: 80px;
  border-radius: var(--radius-full);
  background: var(--accent-primary-light);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent-primary);
  margin-bottom: 20px;
  box-shadow: 0 8px 24px rgba(22, 119, 255, 0.15);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.welcome-state:hover .welcome-icon {
  transform: scale(1.05);
  box-shadow: 0 12px 32px rgba(22, 119, 255, 0.25);
}

.welcome-title {
  font-size: 26px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 10px;
  letter-spacing: -0.3px;
}

.welcome-subtitle {
  font-size: 15px;
  color: var(--text-muted);
  max-width: 420px;
  line-height: 1.6;
  margin: 0 0 32px;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
}

.quick-action {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.25s ease;
  font-family: inherit;
}

.quick-action:hover {
  background: var(--accent-primary-light);
  border-color: var(--accent-primary);
  color: var(--accent-primary);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(22, 119, 255, 0.12);
}

.quick-action:active {
  transform: translateY(0);
}

/* ---- Message Container ---- */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px 16px;
  scroll-behavior: smooth;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.chat-messages::-webkit-scrollbar {
  width: 6px;
}

.chat-messages::-webkit-scrollbar-track {
  background: transparent;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: var(--radius-full);
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: var(--text-muted);
}

/* ---- Message Row ---- */
.message {
  display: flex;
  gap: 10px;
  padding: 8px 0;
  max-width: 1000px;
  width: 100%;
  margin: 0 auto;
  animation: msg-in 0.25s ease;
}

/* 用户消息：头像在右侧，消息气泡在左侧 */
.message.user {
  flex-direction: row-reverse;
}

@keyframes msg-in {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ---- Avatar ---- */
.message-avatar {
  flex-shrink: 0;
  width: 34px;
  height: 34px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tertiary);
  color: var(--text-muted);
  margin-top: 2px;
}

.message.user .message-avatar {
  background: var(--accent-primary-light);
  color: var(--accent-primary);
}

.message.assistant .message-avatar {
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  color: var(--text-inverse);
}

.message.system .message-avatar {
  background: var(--bg-tertiary);
  color: var(--text-muted);
}

/* ---- Message Content ---- */
.message-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

/* ---- Message Bubble ---- */
.message-bubble {
  padding: 10px 14px;
  border-radius: var(--radius-md);
  font-size: 14px;
  line-height: 1.65;
  word-wrap: break-word;
  white-space: pre-wrap;
  transition: box-shadow 0.2s ease;
}

/* User bubble */
.message.user .message-bubble {
  background: var(--accent-primary);
  color: var(--text-inverse);
  border-bottom-right-radius: 4px;
  align-self: flex-end;
  box-shadow: 0 2px 8px rgba(22, 119, 255, 0.2);
}

/* Assistant bubble */
.message.assistant .message-bubble {
  background: var(--bg-secondary);
  color: var(--text-primary);
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
  border: 1px solid var(--border-color);
}

/* System bubble */
.message.system .message-bubble {
  background: var(--bg-tertiary);
  color: var(--text-muted);
  font-size: 13px;
  text-align: center;
  border-radius: var(--radius-sm);
  max-width: 480px;
  margin: 0 auto;
}

/* ---- Markdown Content ---- */
.md-content {
  line-height: 1.7;
}

.md-content :deep(p) {
  margin: 0 0 8px;
}

.md-content :deep(p:last-child) {
  margin-bottom: 0;
}

.md-content :deep(code) {
  background: var(--bg-tertiary);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  color: var(--accent-primary);
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

.md-content :deep(pre) {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 14px 16px;
  overflow-x: auto;
  margin: 10px 0;
}

.md-content :deep(pre code) {
  background: none;
  padding: 0;
  color: var(--text-primary);
  font-size: 13px;
}

.md-content :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 10px 0;
  font-size: 13px;
}

.md-content :deep(th),
.md-content :deep(td) {
  border: 1px solid var(--border-color);
  padding: 8px 12px;
  text-align: left;
}

.md-content :deep(th) {
  background: var(--bg-secondary);
  font-weight: 600;
  color: var(--text-primary);
}

.md-content :deep(blockquote) {
  border-left: 3px solid var(--accent-primary);
  padding: 4px 12px;
  margin: 8px 0;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  border-radius: 0 var(--radius-xs) var(--radius-xs) 0;
}

.md-content :deep(ul),
.md-content :deep(ol) {
  padding-left: 20px;
  margin: 6px 0;
}

.md-content :deep(li) {
  margin: 3px 0;
}

.md-content :deep(h1),
.md-content :deep(h2),
.md-content :deep(h3),
.md-content :deep(h4) {
  margin: 14px 0 8px;
  color: var(--text-primary);
}

.md-content :deep(h1) { font-size: 18px; }
.md-content :deep(h2) { font-size: 16px; }
.md-content :deep(h3) { font-size: 15px; }

.md-content :deep(a) {
  color: var(--accent-primary);
  text-decoration: none;
}

.md-content :deep(a:hover) {
  text-decoration: underline;
}

.md-content :deep(img) {
  max-width: 100%;
  border-radius: var(--radius-sm);
  margin: 8px 0;
}

.md-content :deep(hr) {
  border: none;
  border-top: 1px solid var(--border-color);
  margin: 16px 0;
}

/* ---- Message Time ---- */
.message-time {
  font-size: 11px;
  color: var(--text-muted);
  opacity: 0.6;
  padding: 0 2px;
  margin-top: 2px;
}

.message.user .message-time {
  text-align: right;
}

/* ---- User Attachments ---- */
.user-attachments {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 6px;
}

/* 用户消息中的附件靠右对齐 */
.message.user .user-attachments {
  justify-content: flex-end;
}

.attachment-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  min-width: 160px;
  max-width: 280px;
  transition: all 0.2s ease;
}

.attachment-card:hover {
  border-color: var(--accent-primary);
  box-shadow: 0 2px 8px rgba(22, 119, 255, 0.08);
}

.attachment-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-xs);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 700;
}

.attachment-info {
  flex: 1;
  min-width: 0;
}

.attachment-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attachment-meta {
  font-size: 11px;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 4px;
}

.template-badge {
  color: var(--accent-warning);
  font-weight: 500;
}

.upload-status {
  color: var(--accent-primary);
  font-style: italic;
}

/* ---- Entity & Table Preview ---- */
.entity-preview {
  margin-top: 10px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--bg-primary);
  transition: box-shadow 0.2s ease;
}

.entity-preview:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.entity-preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  gap: 12px;
  flex-wrap: wrap;
}

.entity-preview-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.entity-preview-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.entity-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 500;
  background: var(--accent-primary);
  color: var(--text-inverse);
  border: none;
  border-radius: var(--radius-xs);
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.entity-action-btn:hover {
  background: var(--accent-primary-hover);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(22, 119, 255, 0.25);
}

.entity-action-btn:active {
  transform: translateY(0);
}

.save-to-lib-btn {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}

.save-to-lib-btn:hover {
  background: var(--accent-primary-light);
  color: var(--accent-primary);
  box-shadow: 0 2px 8px rgba(22, 119, 255, 0.1);
}

.entity-table-wrapper {
  overflow-x: auto;
  max-height: 360px;
  overflow-y: auto;
}

.entity-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.entity-table thead {
  position: sticky;
  top: 0;
  z-index: 1;
}

.entity-table th {
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-weight: 600;
  padding: 7px 12px;
  text-align: left;
  white-space: nowrap;
  border-bottom: 1px solid var(--border-color);
  border-right: 1px solid var(--border-color);
}

.entity-table td {
  padding: 6px 12px;
  border-bottom: 1px solid var(--border-color);
  border-right: 1px solid var(--border-color);
  color: var(--text-primary);
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  background: var(--bg-primary);
}

.entity-table tbody tr:hover td {
  background: var(--bg-hover);
}

.entity-preview-more {
  padding: 8px 14px;
  text-align: center;
  font-size: 12px;
  color: var(--text-muted);
  background: var(--bg-primary);
  border-top: 1px solid var(--border-color);
}

/* ---- Table Fill Preview (warm theme) ---- */
.table-fill-preview {
  border-color: var(--accent-warning);
  background: var(--accent-warning-light);
}

.table-fill-preview .entity-preview-header {
  background: var(--accent-warning-light);
  border-bottom-color: var(--accent-warning);
}

.table-fill-preview .entity-table th {
  background: var(--accent-warning-light);
  color: var(--text-primary);
  border-bottom-color: var(--accent-warning);
  border-right-color: var(--accent-warning);
}

.table-fill-preview .entity-table td {
  background: var(--bg-primary);
  border-bottom-color: var(--border-color);
  border-right-color: var(--border-color);
}

.table-fill-preview .entity-table tbody tr:hover td {
  background: var(--bg-hover);
}

.table-fill-stats {
  font-size: 12px;
  color: var(--text-secondary);
}

.table-fill-stats-inline {
  margin-left: 8px;
}

/* ---- Upload Progress Message ---- */
.message-bubble.upload-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  font-size: 13px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
}

.upload-text {
  color: var(--text-muted);
}

/* ---- Progress Card ---- */
.progress-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 14px 18px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.progress-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.progress-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.progress-msg {
  font-size: 12px;
  color: var(--text-muted);
  flex: 1;
  min-width: 60px;
}

.progress-indicator {
  font-size: 10px;
  color: var(--accent-primary);
  animation: pulse 1.2s infinite;
}

.progress-done {
  font-size: 12px;
  color: var(--accent-success);
  font-weight: 600;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.progress-bar-container {
  height: 6px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
  border-radius: var(--radius-full);
  transition: width 0.4s ease;
}

/* ---- Typing Indicator ---- */
.typing-indicator {
  display: inline-flex !important;
  align-items: center;
  gap: 5px;
  padding: 6px 0;
}

.typing-dot {
  width: 7px;
  height: 7px;
  background: var(--text-muted);
  border-radius: 50%;
  animation: typing-bounce 1.4s infinite ease-in-out both;
}

.typing-dot:nth-child(1) { animation-delay: -0.32s; }
.typing-dot:nth-child(2) { animation-delay: -0.16s; }
.typing-dot:nth-child(3) { animation-delay: 0s; }

@keyframes typing-bounce {
  0%, 80%, 100% { transform: scale(0); opacity: 0.3; }
  40% { transform: scale(1); opacity: 1; }
}

/* =============================================================
   Input Area
   ============================================================= */
.chat-input-area {
  border-top: 1px solid var(--border-color);
  background: var(--bg-primary);
  padding: 0 20px 16px;
  flex-shrink: 0;
}

/* ---- Pending Attachments ---- */
.pending-attachments {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 0 8px;
}

.pending-attachment-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  min-width: 140px;
  max-width: 260px;
  transition: all 0.2s ease;
}

.pending-attachment-card:hover {
  border-color: var(--accent-primary);
}

.pending-attachment-card.unselected {
  opacity: 0.5;
}

.pending-attachment-checkbox {
  cursor: pointer;
  accent-color: var(--accent-primary);
}

.pending-attachment-icon {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-xs);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 700;
}

.file-type-label {
  font-size: 10px;
  font-weight: 700;
}

.pending-attachment-body {
  flex: 1;
  min-width: 0;
}

.pending-attachment-name {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 120px;
}

.pending-attachment-meta {
  font-size: 11px;
  color: var(--text-muted);
  display: flex;
  gap: 4px;
  align-items: center;
}

.pending-attachment-kind {
  color: var(--accent-warning);
  font-weight: 500;
}

.pending-attachment-preview-btn {
  height: 26px;
  line-height: 26px;
  padding: 0 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  flex-shrink: 0;
  margin-right: 4px;
  transition: all 0.2s ease;
}

.pending-attachment-preview-btn:hover {
  background: var(--accent-primary);
  color: #fff;
  border-color: var(--accent-primary);
}

.pending-attachment-remove {
  width: 20px;
  height: 20px;
  border-radius: var(--radius-full);
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  transition: all 0.2s ease;
  flex-shrink: 0;
  padding: 0;
}

.pending-attachment-remove:hover {
  background: var(--accent-danger-light);
  color: var(--accent-danger);
}

/* ---- Input Shell ---- */
.chat-input-shell {
  display: flex;
  flex-direction: column;
  gap: 0;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-secondary);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.chat-input-shell:focus-within {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px var(--accent-primary-light);
}

.chat-input {
  display: flex;
  align-items: flex-end;
  padding: 6px 12px;
}

.chat-input textarea {
  flex: 1;
  border: none;
  background: transparent;
  resize: none;
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.5;
  max-height: 200px;
  min-height: 28px;
  padding: 4px 0;
  outline: none;
  font-family: inherit;
}

.chat-input textarea::placeholder {
  color: var(--text-muted);
}

.chat-input.dragover {
  background: var(--accent-primary-light);
  border-radius: var(--radius-sm);
}

/* ---- Input Toolbar ---- */
.chat-input-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px 6px 12px;
  border-top: 1px solid var(--border-color);
  gap: 8px;
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

/* ---- Mode Tabs ---- */
.mode-tabs {
  display: flex;
  gap: 2px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  padding: 2px;
}

.mode-tab {
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  background: transparent;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
  font-family: inherit;
}

.mode-tab:hover {
  color: var(--text-secondary);
  background: var(--bg-hover);
}

.mode-tab.active {
  color: var(--accent-primary);
  background: var(--bg-primary);
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

/* ---- File Type Switcher ---- */
.file-type-switcher {
  display: flex;
  gap: 2px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  padding: 2px;
}

.file-type-btn {
  padding: 5px 10px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  background: transparent;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
  font-family: inherit;
}

.file-type-btn:hover {
  color: var(--text-secondary);
  background: var(--bg-hover);
}

.file-type-btn.active {
  color: var(--accent-primary);
  background: var(--bg-primary);
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.file-type-btn[data-type="template"].active {
  color: var(--accent-warning);
}

/* ---- Toolbar Upload Button ---- */
.toolbar-upload-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 10px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  border: 1px solid transparent;
  border-radius: var(--radius-xs);
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
  white-space: nowrap;
}

.toolbar-upload-btn:hover {
  background: var(--accent-primary-light);
  color: var(--accent-primary);
  border-color: var(--accent-primary);
}

/* ---- File Badges ---- */
.file-count-badges {
  display: flex;
  gap: 4px;
  align-items: center;
}

.file-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 3px 8px;
  font-size: 11px;
  font-weight: 600;
  border-radius: var(--radius-full);
  white-space: nowrap;
}

.file-badge.data-badge {
  background: var(--accent-primary-light);
  color: var(--accent-primary);
}

.file-badge.template-badge {
  background: var(--accent-warning-light);
  color: var(--accent-warning);
}

/* ---- Send Button ---- */
.send-btn {
  width: 34px;
  height: 34px;
  border-radius: var(--radius-full);
  border: none;
  background: var(--accent-primary);
  color: var(--text-inverse);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
  background: var(--accent-primary-hover);
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(22, 119, 255, 0.3);
}

.send-btn:active:not(:disabled) {
  transform: scale(0.95);
}

.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  background: var(--bg-tertiary);
  color: var(--text-muted);
}

.send-btn.loading {
  background: var(--accent-primary);
  opacity: 0.8;
}

.send-spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* =============================================================
   Modals
   ============================================================= */

/* ---- Save to Library Modal ---- */
.save-lib-overlay,
.lib-import-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: overlay-in 0.2s ease;
}

@keyframes overlay-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}

.save-lib-modal,
.lib-import-modal {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  width: 90%;
  max-width: 480px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  animation: modal-in 0.25s ease;
}

@keyframes modal-in {
  from { opacity: 0; transform: translateY(16px) scale(0.97); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}

.save-lib-header,
.lib-import-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px;
  border-bottom: 1px solid var(--border-color);
}

.save-lib-header h3,
.lib-import-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.save-lib-close,
.lib-import-close {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-full);
  border: none;
  background: var(--bg-tertiary);
  color: var(--text-muted);
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  padding: 0;
}

.save-lib-close:hover,
.lib-import-close:hover {
  background: var(--accent-danger-light);
  color: var(--accent-danger);
}

.save-lib-body,
.lib-import-body {
  padding: 18px 22px;
  overflow-y: auto;
  flex: 1;
}

.save-lib-file-info,
.save-lib-space-select {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.save-lib-label {
  font-size: 13px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.save-lib-filename {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.save-lib-select {
  flex: 1;
  padding: 8px 10px;
  font-size: 13px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xs);
  background: var(--bg-primary);
  color: var(--text-primary);
  outline: none;
  font-family: inherit;
}

.save-lib-select:focus {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px var(--accent-primary-light);
}

.save-lib-empty {
  font-size: 13px;
  color: var(--text-muted);
  text-align: center;
  padding: 20px 0;
}

.save-lib-msg {
  font-size: 13px;
  color: var(--accent-danger);
  padding: 8px 0;
}

.save-lib-msg.success {
  color: var(--accent-success);
}

.save-lib-footer,
.lib-import-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 22px;
  border-top: 1px solid var(--border-color);
}

.save-lib-cancel {
  padding: 8px 18px;
  font-size: 13px;
  font-weight: 500;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xs);
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.save-lib-cancel:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.save-lib-confirm,
.lib-import-btn.confirm {
  padding: 8px 18px;
  font-size: 13px;
  font-weight: 500;
  background: var(--accent-primary);
  color: var(--text-inverse);
  border: none;
  border-radius: var(--radius-xs);
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.save-lib-confirm:hover:not(:disabled),
.lib-import-btn.confirm:hover:not(:disabled) {
  background: var(--accent-primary-hover);
  box-shadow: 0 2px 8px rgba(22, 119, 255, 0.25);
}

.save-lib-confirm:disabled,
.lib-import-btn.confirm:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* ---- Library Import Modal ---- */
.lib-import-section {
  margin-bottom: 16px;
}

.lib-import-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.lib-import-select {
  width: 100%;
  padding: 8px 12px;
  font-size: 13px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xs);
  background: var(--bg-primary);
  color: var(--text-primary);
  outline: none;
  font-family: inherit;
}

.lib-import-select:focus {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px var(--accent-primary-light);
}

.lib-import-loading,
.lib-import-empty {
  text-align: center;
  padding: 24px 0;
  font-size: 13px;
  color: var(--text-muted);
}

.lib-import-docs {
  max-height: 280px;
  overflow-y: auto;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xs);
}

.lib-import-doc-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  cursor: pointer;
  transition: all 0.15s ease;
  border-bottom: 1px solid var(--border-color);
}

.lib-import-doc-item:last-child {
  border-bottom: none;
}

.lib-import-doc-item:hover {
  background: var(--bg-hover);
}

.lib-import-doc-item.selected {
  background: var(--accent-primary-light);
}

.lib-import-check {
  width: 20px;
  height: 20px;
  border-radius: var(--radius-xs);
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 11px;
  color: transparent;
  background: var(--bg-primary);
  transition: all 0.2s ease;
}

.lib-import-doc-item.selected .lib-import-check {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
  color: var(--text-inverse);
}

.lib-import-doc-icon {
  color: var(--text-muted);
  flex-shrink: 0;
}

.lib-import-doc-name {
  flex: 1;
  font-size: 13px;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.lib-import-doc-size {
  font-size: 11px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.lib-import-btn.cancel {
  padding: 8px 18px;
  font-size: 13px;
  font-weight: 500;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xs);
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.lib-import-btn.cancel:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

/* =============================================================
   Responsive
   ============================================================= */
@media (max-width: 768px) {
  .chat-messages {
    padding: 16px 14px 12px;
  }

  .message {
    max-width: 100%;
  }

  .welcome-title {
    font-size: 22px;
  }

  .welcome-subtitle {
    font-size: 14px;
  }

  .chat-input-area {
    padding: 0 12px 12px;
  }

  .chat-input-toolbar {
    padding: 6px 8px;
  }

  .mode-tab {
    padding: 4px 8px;
    font-size: 11px;
  }

  .toolbar-upload-btn span {
    display: none;
  }

  .file-type-btn {
    padding: 4px 8px;
    font-size: 11px;
  }

  .send-btn {
    width: 32px;
    height: 32px;
  }

  .quick-action {
    padding: 8px 14px;
    font-size: 12px;
  }

  .save-lib-modal,
  .lib-import-modal {
    max-width: 95%;
    max-height: 90vh;
  }

  .entity-preview-actions {
    flex-direction: column;
    align-items: flex-end;
  }
}

@media (max-width: 480px) {
  .chat-messages {
    padding: 12px 10px 8px;
  }

  .message {
    gap: 8px;
    padding: 6px 0;
  }

  .message-avatar {
    width: 28px;
    height: 28px;
  }

  .message-bubble {
    padding: 8px 12px;
    font-size: 13px;
  }

  .welcome-icon {
    width: 64px;
    height: 64px;
  }

  .welcome-title {
    font-size: 20px;
  }

  .quick-actions {
    gap: 8px;
  }

  .chat-input textarea {
    font-size: 13px;
  }

  .mode-tabs-inline {
    overflow-x: auto;
    max-width: 100%;
  }

  .toolbar-right {
    flex: 1;
    justify-content: flex-end;
  }
}

@media (min-width: 1200px) {
  .chat-messages {
    padding: 24px 40px 20px;
  }

  .message {
    max-width: 1000px;
  }

  .chat-input-area {
    padding: 0 32px 18px;
  }
}

/* =============================================================
   聊天文件预览弹窗
   ============================================================= */
.chat-preview-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: stretch;
  justify-content: center;
  padding: 0;
}

.chat-preview-modal {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  width: 100%;
  max-width: 1400px;
  max-height: 100vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 32px 80px rgba(0, 0, 0, 0.35);
  overflow: hidden;
}

.chat-preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
  background: var(--bg-secondary);
}

.chat-preview-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-preview-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-size: 22px;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all 0.2s;
  flex-shrink: 0;
}

.chat-preview-close:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.chat-preview-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  background: var(--bg-primary);
}

.chat-preview-renderer {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.chat-preview-text {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 24px 28px;
}

.chat-preview-text pre {
  margin: 0;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.8;
  color: var(--text-primary);
  white-space: pre-wrap;
}

.chat-preview-loading,
.chat-preview-error,
.chat-preview-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 100px 24px;
  color: var(--text-muted);
  flex: 1;
}

.chat-preview-loading .loading-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--border-color);
  border-top-color: var(--accent-primary);
  border-radius: 50%;
  animation: chat-spin 0.75s linear infinite;
}

@keyframes chat-spin {
  to { transform: rotate(360deg); }
}

.chat-preview-error {
  color: #ef4444;
}

/* 附件预览按钮 */
.attachment-preview-btn {
  flex-shrink: 0;
  padding: 4px 10px;
  font-size: 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-primary);
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.2s;
  margin-left: 8px;
  align-self: center;
}

.attachment-preview-btn:hover {
  background: var(--bg-hover);
  color: var(--accent-primary);
  border-color: var(--accent-primary);
}

@media (max-width: 768px) {
  .chat-preview-header {
    padding: 12px 16px;
  }
  .chat-preview-text {
    padding: 16px 20px;
  }
}

@media (max-width: 480px) {
  .chat-preview-modal {
    max-height: 100vh;
    border-radius: 0;
  }
}
</style>
