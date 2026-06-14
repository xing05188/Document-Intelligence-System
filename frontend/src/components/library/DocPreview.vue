<script setup>
import { ref, watch } from 'vue'
import libraryApi from '../../api/library'
import SvgIcon from '../icons/SvgIcon.vue'

const props = defineProps({
  doc: { type: Object, default: null },
  visible: { type: Boolean, default: false },
})

const emit = defineEmits(['close'])

const loading = ref(false)
const error = ref('')
const previewData = ref(null)

function getDownloadUrl(docId) {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
  return `${baseUrl}/api/library/docs/${docId}/download`
}

function handleClose() {
  previewData.value = null
  emit('close')
}

watch(() => props.visible, async (newVal) => {
  if (newVal && props.doc) {
    await loadPreview()
  }
})

async function loadPreview() {
  loading.value = true
  error.value = ''
  previewData.value = null
  try {
      const res = await libraryApi.previewDoc(props.doc.id)
      previewData.value = res
  } catch (e) {
    error.value = e.message || '预览加载失败'
  } finally {
    loading.value = false
  }
}

function renderMarkdown(text) {
  if (!text) return ''
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/^#### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    .replace(/`(.+?)`/g, '<code>$1</code>')
    .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>')
  return '<p>' + html + '</p>'
}

function getFileLabel(ext) {
  const labels = {
    '.txt': '纯文本', '.md': 'Markdown', '.pdf': 'PDF',
    '.docx': 'Word', '.doc': 'Word',
    '.xlsx': 'Excel', '.xls': 'Excel',
    '.png': '图片', '.jpg': '图片', '.jpeg': '图片',
    '.gif': '图片', '.webp': '图片', '.svg': '图片',
    '.bmp': '图片', '.ico': '图片',
  }
  return labels[ext] || '文档'
}
</script>

<template>
  <Teleport to="body">
    <div class="preview-overlay" :class="{ active: visible }" @click.self="handleClose">
      <div class="preview-modal">
        <!-- Header -->
        <div class="preview-header">
          <div class="preview-header-left">
            <SvgIcon name="file" :size="20" />
            <span class="preview-filename">{{ doc?.name || '' }}</span>
            <span class="preview-badge">{{ getFileLabel(doc?.file_extension || '') }}</span>
          </div>
          <button class="preview-close" @click="handleClose">×</button>
        </div>

        <!-- Body -->
        <div class="preview-body">
          <!-- Loading -->
          <div v-if="loading" class="preview-loading">
            <div class="loading-spinner"></div>
            <span>正在加载预览...</span>
          </div>

          <!-- Error -->
          <div v-else-if="error" class="preview-error">
            <SvgIcon name="warning" :size="24" />
            <span>{{ error }}</span>
          </div>

          <!-- Image Preview -->
          <div v-else-if="previewData?.type === 'image'" class="preview-image-container">
            <img
              :src="getDownloadUrl(doc.id)"
              :alt="doc?.name"
              class="preview-image"
              @error="error = '图片加载失败'"
            />
          </div>

          <!-- Text Preview -->
          <div v-else-if="previewData?.type === 'text'" class="preview-text-container">
            <!-- Markdown rendered -->
            <div
              v-if="doc?.file_extension === '.md'"
              class="preview-markdown"
              v-html="renderMarkdown(previewData.content)"
            ></div>
            <!-- Plain text -->
            <pre v-else class="preview-text">{{ previewData.content }}</pre>
          </div>

          <!-- No data -->
          <div v-else-if="!loading && !error" class="preview-empty">
            <span>无法预览此文件</span>
          </div>
        </div>

        <!-- Footer -->
        <div class="preview-footer">
          <span class="preview-info">{{ previewData?.content?.length || 0 }} 字符</span>
          <button class="preview-btn close-btn" @click="handleClose">关闭</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.preview-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.25s ease;
  padding: 24px;
}

.preview-overlay.active {
  opacity: 1;
  pointer-events: auto;
}

.preview-modal {
  background: var(--bg-primary);
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 960px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

/* Header */
.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.preview-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.preview-filename {
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.preview-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--bg-tertiary);
  color: var(--text-muted);
  flex-shrink: 0;
}

.preview-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-muted);
  font-size: 22px;
  font-weight: 300;
  transition: all 0.2s;
  flex-shrink: 0;
}

.preview-close:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

/* Body */
.preview-body {
  flex: 1;
  overflow-y: auto;
  min-height: 300px;
  max-height: 65vh;
}

/* Loading */
.preview-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 80px 24px;
  color: var(--text-muted);
}

.loading-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--border-color);
  border-top-color: var(--accent-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Error */
.preview-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 80px 24px;
  color: #ef4444;
}

/* Empty */
.preview-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80px 24px;
  color: var(--text-muted);
}

/* Image */
.preview-image-container {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  min-height: 300px;
}

.preview-image {
  max-width: 100%;
  max-height: 60vh;
  object-fit: contain;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

/* Text */
.preview-text-container {
  padding: 0;
}

.preview-text {
  margin: 0;
  padding: 20px 24px;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow-x: auto;
  color: var(--text-primary);
}

/* Markdown */
.preview-markdown {
  padding: 24px 32px;
  font-size: 15px;
  line-height: 1.8;
  color: var(--text-primary);
  max-width: 100%;
}

.preview-markdown :deep(h1),
.preview-markdown :deep(h2),
.preview-markdown :deep(h3),
.preview-markdown :deep(h4) {
  margin-top: 1.5em;
  margin-bottom: 0.6em;
  font-weight: 700;
  line-height: 1.3;
}

.preview-markdown :deep(h1) { font-size: 1.6em; }
.preview-markdown :deep(h2) { font-size: 1.35em; }
.preview-markdown :deep(h3) { font-size: 1.2em; }
.preview-markdown :deep(h4) { font-size: 1.1em; }

.preview-markdown :deep(p) {
  margin: 0.8em 0;
}

.preview-markdown :deep(code) {
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 0.9em;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--bg-tertiary);
}

.preview-markdown :deep(pre) {
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  padding: 16px 20px;
  overflow-x: auto;
  margin: 1em 0;
}

.preview-markdown :deep(pre code) {
  padding: 0;
  background: none;
  font-size: 13px;
  line-height: 1.6;
}

.preview-markdown :deep(a) {
  color: var(--accent-primary);
  text-decoration: none;
}

.preview-markdown :deep(a:hover) {
  text-decoration: underline;
}

.preview-markdown :deep(li) {
  margin: 0.3em 0 0.3em 1.5em;
}

.preview-markdown :deep(strong) {
  font-weight: 700;
}

/* Footer */
.preview-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
  border-top: 1px solid var(--border-color);
  flex-shrink: 0;
}

.preview-info {
  font-size: 12px;
  color: var(--text-muted);
}

.preview-btn {
  padding: 8px 20px;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.preview-btn.close-btn {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
}

.preview-btn.close-btn:hover {
  background: var(--bg-hover);
  border-color: var(--border-color-hover);
}
</style>