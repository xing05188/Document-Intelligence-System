<script setup>
import { ref, onMounted, watch } from 'vue'
import mammoth from 'mammoth'

const props = defineProps({
  blob: { type: Blob, default: null },
})

const htmlContent = ref('')
const loading = ref(true)
const error = ref('')

async function renderDocx() {
  if (!props.blob) return
  loading.value = true
  error.value = ''
  htmlContent.value = ''
  try {
    const arrayBuffer = await props.blob.arrayBuffer()
    const result = await mammoth.convertToHtml({ arrayBuffer })
    htmlContent.value = result.value
    if (result.messages && result.messages.length > 0) {
      console.warn('mammoth messages:', result.messages)
    }
  } catch (e) {
    error.value = e.message || '文档渲染失败'
  } finally {
    loading.value = false
  }
}

onMounted(renderDocx)
watch(() => props.blob, renderDocx)
</script>

<template>
  <div class="docx-renderer">
    <div v-if="loading" class="docx-loading">
      <div class="loading-spinner"></div>
      <span>正在解析 Word 文档...</span>
    </div>
    <div v-else-if="error" class="docx-error">{{ error }}</div>
    <div v-else class="docx-content" v-html="htmlContent"></div>
  </div>
</template>

<style scoped>
.docx-renderer {
  min-height: 200px;
}

.docx-loading {
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

.docx-error {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80px 24px;
  color: #ef4444;
  font-size: 15px;
}

.docx-content {
  padding: 28px 36px;
  font-size: 15px;
  line-height: 1.8;
  color: var(--text-primary);
}

.docx-content :deep(h1),
.docx-content :deep(h2),
.docx-content :deep(h3),
.docx-content :deep(h4) {
  margin-top: 1.5em;
  margin-bottom: 0.5em;
  font-weight: 700;
  color: var(--text-primary);
}

.docx-content :deep(h1) { font-size: 1.6em; }
.docx-content :deep(h2) { font-size: 1.35em; }
.docx-content :deep(h3) { font-size: 1.15em; }
.docx-content :deep(h4) { font-size: 1.05em; }

.docx-content :deep(p) {
  margin: 0.7em 0;
}

.docx-content :deep(img) {
  max-width: 100%;
  border-radius: var(--radius-md);
  margin: 0.8em 0;
}

.docx-content :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 1em 0;
  font-size: 14px;
}

.docx-content :deep(th),
.docx-content :deep(td) {
  border: 1px solid var(--border-color);
  padding: 8px 12px;
  text-align: left;
}

.docx-content :deep(th) {
  background: var(--bg-secondary);
  font-weight: 600;
}

.docx-content :deep(tr:nth-child(even)) {
  background: var(--bg-tertiary);
}

.docx-content :deep(ul),
.docx-content :deep(ol) {
  padding-left: 1.6em;
  margin: 0.5em 0;
}

.docx-content :deep(li) {
  margin: 0.25em 0;
}

.docx-content :deep(strong) {
  font-weight: 700;
}

.docx-content :deep(a) {
  color: var(--accent-primary);
  text-decoration: none;
}

.docx-content :deep(a:hover) {
  text-decoration: underline;
}

@media (max-width: 768px) {
  .docx-content { padding: 20px 24px; font-size: 14px; }
}

@media (max-width: 480px) {
  .docx-content { padding: 16px 16px; font-size: 13px; }
}
</style>