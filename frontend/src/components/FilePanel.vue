<script setup>
import { computed, ref } from 'vue'
import { NUpload, NButton, NTag, NScrollbar, useMessage } from 'naive-ui'
import { useSessionStore } from '../stores/sessionStore'

const message = useMessage()
const sessionStore = useSessionStore()
const uploadingCount = ref(0)
const isUploading = computed(() => uploadingCount.value > 0)
const activeTab = ref('data')

// 上传区域只显示临时文件
const tempDataFiles = computed(() => sessionStore.tempDataFiles)
const tempTemplateFiles = computed(() => sessionStore.tempTemplateFiles)

// 根据当前模式判断是否需要显示数据文件
const showDataTab = computed(() => {
  return sessionStore.currentModeConfig.requiresData !== false
})

// 根据当前模式判断是否需要显示模板
const showTemplateTab = computed(() => {
  const config = sessionStore.currentModeConfig
  return config.requiresTemplate !== false
})

// 整个上传区域是否显示
const showUploadPanel = computed(() => {
  return showDataTab.value || showTemplateTab.value
})

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function getFileTypeTag(type) {
  const ext = type.split('.').pop().toLowerCase()
  const map = {
    pdf:  { tag: 'error',   label: 'PDF' },
    doc:  { tag: 'info',   label: 'DOC' },
    docx: { tag: 'info',   label: 'DOCX' },
    xls:  { tag: 'success', label: 'XLS' },
    xlsx: { tag: 'success', label: 'XLSX' },
    txt:  { tag: 'default', label: 'TXT' },
    md:   { tag: 'default', label: 'MD' },
    csv:  { tag: 'warning', label: 'CSV' },
    png:  { tag: 'info',   label: 'PNG' },
    jpg:  { tag: 'info',   label: 'JPG' },
    jpeg: { tag: 'info',   label: 'JPEG' },
  }
  const item = map[ext]
  return item ? { tag: item.tag, label: item.label } : { tag: 'default', label: ext.toUpperCase() }
}

function getFileIcon(type) {
  const ext = type.split('.').pop().toLowerCase()
  if (['pdf'].includes(ext)) return '📄'
  if (['doc', 'docx'].includes(ext)) return '📝'
  if (['xls', 'xlsx', 'csv'].includes(ext)) return '📊'
  if (['png', 'jpg', 'jpeg'].includes(ext)) return '🖼️'
  return '📎'
}

async function handleUploadRequest(options, fileType) {
  const uploadInfo = options?.file
  const rawFile = uploadInfo?.file || uploadInfo
  if (!rawFile) {
    options?.onError?.()
    message.error('上传失败: 无法读取文件对象')
    return
  }

  // 无会话时自动创建（沿用当前选中的模式）
  if (!sessionStore.currentSessionId) {
    await sessionStore.createSession()
  }
  uploadingCount.value += 1
  try {
    await sessionStore.uploadFile(rawFile, fileType)
    options?.onFinish?.()
    message.success('上传成功')
  } catch (e) {
    options?.onError?.()
    message.error('上传失败: ' + e.message)
  } finally {
    uploadingCount.value = Math.max(0, uploadingCount.value - 1)
  }
}

// 当前标签对应的文件列表
const currentFiles = computed(() => {
  return activeTab.value === 'data' ? tempDataFiles.value : tempTemplateFiles.value
})

// 当前上传类型
const currentUploadType = computed(() => {
  return activeTab.value
})
</script>

<template>
  <div v-if="showUploadPanel" class="file-panel">
    <!-- 标签页切换 -->
    <div class="tabs">
      <button
        v-if="showDataTab"
        :class="['tab', { active: activeTab === 'data' }]"
        @click="activeTab = 'data'"
      >
        数据文件
        <span class="tab-count">({{ tempDataFiles.length }})</span>
      </button>
      <button
        v-if="showTemplateTab"
        :class="['tab', { active: activeTab === 'template' }]"
        @click="activeTab = 'template'"
      >
        模板文件
        <span class="tab-count">({{ tempTemplateFiles.length }})</span>
      </button>
    </div>

    <!-- 拖拽上传区域 -->
    <n-upload
      :custom-request="(options) => handleUploadRequest(options, currentUploadType)"
      :show-file-list="false"
      :disabled="isUploading"
      accept=".pdf,.doc,.docx,.xls,.xlsx,.txt,.md"
      multiple
      drag
      class="upload-area"
    >
      <div class="upload-content">
        <svg xmlns="http://www.w3.org/2000/svg" class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
        <div class="upload-text">
          <span class="upload-hint">拖拽文件到此处，或</span>
          <span class="upload-action">点击上传</span>
        </div>
      </div>
    </n-upload>

    <!-- 文件列表 -->
    <div v-if="currentFiles.length > 0" class="file-list">
      <div
        v-for="file in currentFiles"
        :key="file.id"
        class="file-card"
      >
        <input
          type="checkbox"
          :checked="file.is_selected"
          @change="sessionStore.toggleFileSelection(file.id, activeTab, $event.target.checked)"
          class="file-checkbox"
        />
        <span class="file-icon">{{ getFileIcon(file.file_name) }}</span>
        <div class="file-info">
          <span class="file-name">{{ file.file_name }}</span>
          <span class="file-size">{{ formatSize(file.file_size) }}</span>
        </div>
        <n-tag :type="getFileTypeTag(file.file_name).tag" size="small" class="file-tag">
          {{ getFileTypeTag(file.file_name).label }}
        </n-tag>
        <button
          @click="sessionStore.deleteFile(file.id, activeTab)"
          class="file-delete"
          title="删除"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="delete-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
    </div>
    <div v-else class="empty-state">
      <span>暂无{{ activeTab === 'data' ? '数据' : '模板' }}文件</span>
    </div>
  </div>
</template>

<style scoped>
.file-panel {
  padding: 12px 16px;
}

.tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 12px;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 8px;
}

.tab {
  padding: 6px 16px;
  border: none;
  background: transparent;
  color: #6b7280;
  font-size: 14px;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s;
}

.tab:hover {
  background: #f3f4f6;
  color: #374151;
}

.tab.active {
  background: #18a058;
  color: white;
}

.tab-count {
  font-size: 12px;
  opacity: 0.7;
}

.upload-area {
  width: 100%;
  margin-bottom: 12px;
}

.upload-area :deep(.n-upload-dragger) {
  padding: 20px;
  background: #f9fafb;
  border: 2px dashed #d1d5db;
  border-radius: 8px;
  transition: all 0.2s;
}

.upload-area :deep(.n-upload-dragger:hover) {
  border-color: #18a058;
  background: #f0fdf4;
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-icon {
  width: 32px;
  height: 32px;
  color: #9ca3af;
}

.upload-text {
  display: flex;
  gap: 4px;
  font-size: 14px;
}

.upload-hint {
  color: #6b7280;
}

.upload-action {
  color: #18a058;
  font-weight: 500;
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 180px;
  overflow-y: auto;
}

.file-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  transition: all 0.2s;
}

.file-card:hover {
  border-color: #d1d5db;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.file-card:has(.file-checkbox:checked) {
  background: #f0fdf4;
  border-color: #86efac;
}

.file-checkbox {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: #18a058;
}

.file-icon {
  font-size: 20px;
}

.file-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.file-name {
  font-size: 14px;
  color: #374151;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-size {
  font-size: 12px;
  color: #9ca3af;
}

.file-tag {
  flex-shrink: 0;
}

.file-delete {
  padding: 4px;
  border: none;
  background: transparent;
  color: #9ca3af;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.file-delete:hover {
  background: #fee2e2;
  color: #ef4444;
}

.delete-icon {
  width: 16px;
  height: 16px;
}

.empty-state {
  padding: 20px;
  text-align: center;
  color: #9ca3af;
  font-size: 14px;
}
</style>
