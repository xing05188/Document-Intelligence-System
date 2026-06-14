<script setup>
defineOptions({ name: 'ChatView' })

import { ref, onMounted, onUnmounted, nextTick, watch, computed } from 'vue'
import { marked } from 'marked'
import { useSessionStore } from '../../stores/sessionStore'
import { useFileStore } from '../../stores/fileStore'
import { useLibraryStore } from '../../stores/libraryStore'
import libraryApi from '../../api/library'
import SvgIcon from '../icons/SvgIcon.vue'

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
  input.accept = '.pdf,.doc,.docx,.xlsx,.xls,.txt'
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
    fileStore.addLibraryFile(doc)
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
  }
  return map[ext] || { bg: 'rgba(161, 161, 170, 0.15)', text: '#a1a1aa', icon: 'file' }
}

function getFileLabel(fileName) {
  const ext = (fileName || '').split('.').pop().toLowerCase()
  const map = {
    pdf: 'PDF', doc: 'DOC', docx: 'DOCX',
    xls: 'XLS', xlsx: 'XLSX',
    txt: 'TXT', md: 'MD', csv: 'CSV',
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
                        :key="f.file_id ?? f.file_path"
                        class="entity-action-btn"
                        type="button"
                        @click="downloadResultFile(f)"
                      >
                        {{ getFileExt(f.file_name) }} ↓
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
                      :key="f.file_id ?? f.file_path"
                      class="entity-action-btn"
                      type="button"
                      @click="downloadResultFile(f)"
                    >
                      {{ getFileExt(f.file_name) }} ↓
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
                      <button v-for="f in msg.generated_files" :key="f.file_id ?? f.file_path" class="entity-action-btn" @click="downloadResultFile(f)">
                        {{ getFileExt(f.file_name) }} ↓
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
                    <button v-for="f in msg.generated_files" :key="f.file_id" class="entity-action-btn" @click="downloadResultFile(f)">
                      {{ getFileExt(f.file_name) }} ↓
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
                    <button v-for="f in msg.generated_files" :key="f.file_id" class="entity-action-btn" @click="downloadResultFile(f)">
                      {{ getFileExt(f.file_name) }} ↓
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
                    <button v-for="f in msg.generated_files" :key="f.file_id" class="entity-action-btn" @click="downloadResultFile(f)">
                      {{ getFileExt(f.file_name) }} ↓
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
</template>

<style scoped>
/* 进度条 */
.progress-card {
  background: #f9fafb;
  border-radius: 8px;
  padding: 12px 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.progress-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.progress-title {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.progress-msg {
  font-size: 12px;
  color: #9ca3af;
  flex: 1;
}

.progress-indicator {
  font-size: 12px;
  color: #9ca3af;
  animation: pulse 1s infinite;
}

.progress-done {
  font-size: 12px;
  color: #10b981;
  font-weight: 500;
}

.progress-bar-container {
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #10b981, #34d399);
  border-radius: 4px;
  transition: width 0.3s ease;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* ============ 实体提取表格预览 ============ */
.entity-preview {
  margin-top: 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  overflow: hidden;
  background: white;
}

.entity-preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: white;
  border-bottom: 1px solid #e5e7eb;
}

.entity-preview-title {
  font-size: 13px;
  font-weight: 500;
  color: #111827;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.entity-preview-actions {
  display: flex;
  gap: 6px;
}

.entity-action-btn {
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 3px 10px;
  font-size: 12px;
  cursor: pointer;
}

.entity-action-btn:hover {
  background: #2563eb;
}

.entity-table-wrapper {
  overflow-x: auto;
  max-height: 400px;
  overflow-y: auto;
}

.entity-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  background: white;
}

.entity-table thead {
  position: sticky;
  top: 0;
  z-index: 1;
}

.entity-table th {
  background: white;
  color: #111827;
  font-weight: 600;
  padding: 6px 10px;
  text-align: left;
  white-space: nowrap;
  border-bottom: 1px solid #d1d5db;
  border-right: 1px solid #e5e7eb;
}

.entity-table td {
  padding: 5px 10px;
  border-bottom: 1px solid #f3f4f6;
  border-right: 1px solid #f9fafb;
  color: #111827;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  background: white;
}

.entity-table tbody tr:hover td {
  background: #f0f9ff;
}

.entity-preview-more {
  padding: 8px 12px;
  text-align: center;
  font-size: 12px;
  color: #6b7280;
  background: white;
  border-top: 1px solid #e5e7eb;
}

.table-fill-preview {
  border-color: #fcd34d;
  background: #fffbeb;
}

.table-fill-preview .entity-preview-header {
  background: #fffbeb;
  border-bottom: 1px solid #fde68a;
}

.table-fill-preview .entity-preview-title {
  color: #78350f;
}

.table-fill-preview .entity-table th {
  background: #fef3c7;
  color: #78350f;
  border-bottom: 1px solid #fcd34d;
  border-right: 1px solid #fde68a;
}

.table-fill-preview .entity-table td {
  border-bottom: 1px solid #fef3c7;
  border-right: 1px solid #fefce8;
  background: #ffffff;
}

.table-fill-preview .entity-table tbody tr:hover td {
  background: #fff7ed;
}

.table-fill-preview .entity-preview-more {
  background: #fffbeb;
  border-top: 1px solid #fde68a;
  color: #92400e;
}

.table-fill-stats {
  font-size: 12px;
  color: #92400e;
  white-space: nowrap;
}

.table-fill-stats-inline {
  margin-left: 8px;
  font-weight: 500;
}

/* Loading 动画 */
.typing-indicator {
  display: inline-flex !important;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  padding: 4px 0;
}

.typing-dot {
  width: 6px;
  height: 6px;
  background: #6b7280;
  border-radius: 50%;
  animation: typing-bounce 1.4s infinite ease-in-out both;
}

.typing-dot:nth-child(1) {
  animation-delay: -0.32s;
}

.typing-dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes typing-bounce {
  0%, 80%, 100% {
    transform: scale(0);
    opacity: 0.4;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}
</style>
