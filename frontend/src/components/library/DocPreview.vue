<script setup>
import { ref, watch, computed } from 'vue'
import libraryApi from '../../api/library'
import SvgIcon from '../icons/SvgIcon.vue'
import MarkdownRenderer from './MarkdownRenderer.vue'
import JsonRenderer from './JsonRenderer.vue'
import DocxRenderer from './DocxRenderer.vue'
import PdfRenderer from './PdfRenderer.vue'
import ExcelRenderer from './ExcelRenderer.vue'

const props = defineProps({
  doc: { type: Object, default: null },
  visible: { type: Boolean, default: false },
  // 可选的自定义 fetch 函数（非文档库文件预览，如工作流文件、本地上传文件）
  fetchPreviewPdf: { type: Function, default: null },   // (doc) => Promise<Blob>
  fetchDownload: { type: Function, default: null },     // (doc) => Promise<Blob>
  fetchPreview: { type: Function, default: null },       // (doc) => Promise<Object>
  downloadUrl: { type: String, default: '' },            // 自定义下载 URL（空时自动从 doc.id 生成）
})

const emit = defineEmits(['close'])

const loading = ref(false)
const error = ref('')
const previewData = ref(null)
const fileBlob = ref(null)

// 判断文档类型
const docType = computed(() => {
  if (!props.doc) return 'unknown'
  const ext = (props.doc.file_extension || '').toLowerCase().replace(/^\./, '')
  if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp', 'ico'].includes(ext)) return 'image'
  if (ext === 'md') return 'markdown'
  if (ext === 'json') return 'json'
  if (ext === 'txt') return 'text'
  if (['docx', 'doc'].includes(ext)) return 'docx'
  if (['xlsx', 'xls'].includes(ext)) return 'excel'
  if (ext === 'pdf') return 'pdf'
  return 'unknown'
})

// 是否为二进制格式（docx/excel 直接从 download 获取 blob）
const isBinaryFormat = computed(() => {
  return ['docx', 'excel'].includes(docType.value)
})

// PDF 是否需走 /preview-pdf 转换
const isPdfFormat = computed(() => {
  return docType.value === 'pdf'
})

function getDownloadUrl(docId) {
  if (props.downloadUrl) return props.downloadUrl
  const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
  return `${baseUrl}/api/library/docs/${docId}/download`
}

function handleClose() {
  previewData.value = null
  fileBlob.value = null
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
  fileBlob.value = null

  try {
    if (docType.value === 'pdf') {
      // PDF → 调用 /preview-pdf 端点（直接返回 PDF 流）
      const fn = props.fetchPreviewPdf || (doc => libraryApi.previewDocAsPdf(doc.id))
      const res = await fn(props.doc)
      fileBlob.value = res
    } else if (isBinaryFormat.value) {
      // docx/excel → 从 download 端点获取原始 blob，用各自渲染器
      const fn = props.fetchDownload || (doc => libraryApi.downloadDocBlob(doc.id))
      const res = await fn(props.doc)
      fileBlob.value = res
    } else {
      // 文本格式 → 从 preview 端点获取文本
      const fn = props.fetchPreview || (doc => libraryApi.previewDoc(doc.id))
      const res = await fn(props.doc)
      previewData.value = res
    }
  } catch (e) {
    error.value = e.message || '预览加载失败'
  } finally {
    loading.value = false
  }
}

function getFileLabel(ext) {
  const key = (ext || '').toLowerCase().replace(/^\./, '')
  const labels = {
    'txt': '纯文本', 'md': 'Markdown', 'json': 'JSON', 'pdf': 'PDF',
    'docx': 'Word', 'doc': 'Word',
    'xlsx': 'Excel', 'xls': 'Excel',
    'png': '图片', 'jpg': '图片', 'jpeg': '图片',
    'gif': '图片', 'webp': '图片', 'svg': '图片',
    'bmp': '图片', 'ico': '图片',
  }
  return labels[key] || '文档'
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
          <div v-else-if="docType === 'image'" class="preview-image-container">
            <img
              :src="getDownloadUrl(doc.id)"
              :alt="doc?.name"
              class="preview-image"
              @error="error = '图片加载失败'"
            />
          </div>

          <!-- Markdown Preview -->
          <div v-else-if="docType === 'markdown' && previewData?.content" class="preview-renderer-wrapper">
            <MarkdownRenderer :content="previewData.content" />
          </div>

          <!-- Plain Text Preview -->
          <div v-else-if="docType === 'text' && previewData?.content" class="preview-text-container">
            <pre class="preview-text">{{ previewData.content }}</pre>
          </div>

          <!-- JSON Preview -->
          <div v-else-if="docType === 'json' && previewData?.content" class="preview-renderer-wrapper">
            <JsonRenderer :content="previewData.content" />
          </div>

          <!-- Word Document Preview (原生渲染) -->
          <div v-else-if="docType === 'docx' && fileBlob" class="preview-renderer-wrapper">
            <DocxRenderer :blob="fileBlob" />
          </div>

          <!-- PDF Preview (浏览器原生渲染) -->
          <div v-else-if="docType === 'pdf' && fileBlob" class="preview-renderer-wrapper">
            <PdfRenderer :blob="fileBlob" />
          </div>

          <!-- Excel Preview (原生渲染) -->
          <div v-else-if="docType === 'excel' && fileBlob" class="preview-renderer-wrapper">
            <ExcelRenderer :blob="fileBlob" />
          </div>

          <!-- No data / Unknown type -->
          <div v-else-if="!loading && !error" class="preview-empty">
            <span>无法预览此文件</span>
          </div>
        </div>

        <!-- Footer -->
        <div class="preview-footer">
          <span class="preview-info" v-if="previewData?.content">
            {{ previewData.content.length }} 字符
          </span>
          <span class="preview-info" v-else-if="fileBlob">
            {{ (fileBlob.size / 1024).toFixed(1) }} KB
          </span>
          <span class="preview-info" v-else></span>
          <button class="preview-btn close-btn" @click="handleClose">关闭</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
/* =============================================================
   DocPreview.vue — 统一预览弹窗
   ============================================================= */

/* ---- Overlay ---- */
.preview-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  z-index: 1000;
  display: flex;
  align-items: stretch;
  justify-content: center;
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transition: all 0.3s ease;
  padding: 0;
}

.preview-overlay.active {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
}

/* ---- Modal ---- */
.preview-modal {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 1400px;
  max-height: 100vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 32px 80px rgba(0, 0, 0, 0.35);
  overflow: hidden;
  transform: scale(0.95) translateY(20px);
  transition: transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.preview-overlay.active .preview-modal {
  transform: scale(1) translateY(0);
}

/* ---- Header ---- */
.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 28px;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
  background: var(--bg-secondary);
}

.preview-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.preview-filename {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.preview-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 4px;
  background: var(--bg-tertiary);
  color: var(--text-muted);
  flex-shrink: 0;
  border: 1px solid var(--border-color);
}

.preview-close {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--text-muted);
  font-size: 24px;
  font-weight: 400;
  transition: all 0.2s ease;
  flex-shrink: 0;
  line-height: 1;
}

.preview-close:hover {
  background: var(--bg-hover);
  border-color: var(--border-color);
  color: var(--text-primary);
}

/* ---- Body ---- */
.preview-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  background: var(--bg-primary);
}

.preview-renderer-wrapper {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

/* ---- Loading State ---- */
.preview-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
  padding: 100px 24px;
  color: var(--text-muted);
  flex: 1;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-color);
  border-top-color: var(--accent-primary);
  border-radius: 50%;
  animation: spin 0.75s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ---- Error State ---- */
.preview-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 100px 24px;
  color: #ef4444;
  font-size: 15px;
  flex: 1;
}

/* ---- Empty State ---- */
.preview-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 100px 24px;
  color: var(--text-muted);
  font-size: 15px;
  flex: 1;
}

/* ---- Image Preview ---- */
.preview-image-container {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 28px;
  min-height: 200px;
  background: rgba(0, 0, 0, 0.02);
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.preview-image {
  max-width: 100%;
  max-height: 60vh;
  object-fit: contain;
  border-radius: var(--radius-md);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  transition: box-shadow 0.3s ease;
}

.preview-image:hover {
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
}

/* ---- Text Preview ---- */
.preview-text-container {
  padding: 0;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

.preview-text {
  margin: 0;
  padding: 24px 28px;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.8;
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow-x: auto;
  color: var(--text-primary);
  tab-size: 2;
}

/* ---- Footer ---- */
.preview-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 28px;
  border-top: 1px solid var(--border-color);
  flex-shrink: 0;
  background: var(--bg-secondary);
}

.preview-info {
  font-size: 12px;
  color: var(--text-muted);
}

/* Footer Button */
.preview-btn {
  padding: 8px 20px;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.close-btn {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
}

.close-btn:hover {
  background: var(--bg-hover);
  border-color: var(--border-color-hover);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

/* =============================================================
   Responsive
   ============================================================= */
@media (max-width: 768px) {
  .preview-overlay {
    padding: 12px;
  }

  .preview-modal {
    max-width: 100%;
    max-height: 100vh;
    border-radius: var(--radius-lg);
  }

  .preview-header {
    padding: 14px 18px;
  }

  .preview-filename {
    font-size: 14px;
  }

  .preview-body {
    max-height: none;
    min-height: 150px;
  }

  .preview-text {
    padding: 16px 20px;
    font-size: 12px;
  }

  .preview-image-container {
    padding: 16px;
  }

  .preview-footer {
    padding: 12px 20px;
  }
}

@media (max-width: 480px) {
  .preview-overlay {
    padding: 0;
  }

  .preview-modal {
    max-width: 100%;
    max-height: 100vh;
    border-radius: 0;
  }

  .preview-header {
    padding: 14px 16px;
  }

  .preview-header-left {
    gap: 8px;
  }

  .preview-badge {
    display: none;
  }

  .preview-text {
    padding: 12px 16px;
    font-size: 12px;
  }

  .preview-image-container {
    padding: 12px;
  }

  .preview-footer {
    padding: 10px 16px;
  }
}
</style>