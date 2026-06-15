<script setup>
/**
 * PDF 预览组件
 * 使用 Blob URL + <embed> 方式，调用浏览器原生 PDF 渲染引擎
 * 比 PDF.js canvas 渲染更稳定、更快、功能更全（内置搜索/缩放/打印/翻页）
 */
import { ref, onMounted, watch, onUnmounted } from 'vue'

const props = defineProps({
  blob: { type: Blob, default: null },
})

const loading = ref(true)
const error = ref('')
const pdfUrl = ref('')

let objectUrl = null

function createPdfUrl() {
  if (!props.blob) {
    error.value = 'PDF 数据为空'
    loading.value = false
    return
  }

  // 清理旧的 URL
  if (objectUrl) {
    URL.revokeObjectURL(objectUrl)
    objectUrl = null
  }

  try {
    objectUrl = URL.createObjectURL(props.blob)
    pdfUrl.value = objectUrl
    error.value = ''
  } catch (e) {
    error.value = '创建预览链接失败: ' + (e.message || '')
  } finally {
    loading.value = false
  }
}

onMounted(createPdfUrl)

onUnmounted(() => {
  if (objectUrl) {
    URL.revokeObjectURL(objectUrl)
    objectUrl = null
  }
  pdfUrl.value = ''
})

watch(() => props.blob, () => {
  loading.value = true
  error.value = ''
  createPdfUrl()
})
</script>

<template>
  <div class="pdf-renderer">
    <!-- Loading state -->
    <div v-if="loading" class="pdf-loading">
      <div class="loading-spinner"></div>
      <span>正在加载 PDF...</span>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="pdf-error">{{ error }}</div>

    <!-- PDF embed -->
    <div v-else class="pdf-container">
      <embed
        v-if="pdfUrl"
        :src="pdfUrl"
        type="application/pdf"
        class="pdf-embed"
        title="PDF 预览"
      />
    </div>
  </div>
</template>

<style scoped>
.pdf-renderer {
  min-height: 200px;
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
}

.pdf-loading {
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
  animation: spin 0.75s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.pdf-error {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80px 24px;
  color: #ef4444;
  font-size: 15px;
}

.pdf-container {
  flex: 1;
  display: flex;
  min-height: 0;
}

.pdf-embed {
  flex: 1;
  min-height: 0;
  border: none;
}
</style>