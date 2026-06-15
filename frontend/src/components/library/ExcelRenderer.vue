<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import * as XLSX from 'xlsx'

const props = defineProps({
  blob: { type: Blob, default: null },
})

const loading = ref(true)
const error = ref('')
const sheetNames = ref([])
const currentSheet = ref('')
const sheetHtml = ref('')
const sheetData = ref(null) // workbook 引用
const tableRef = ref(null)  // 表格容器引用

async function renderExcel() {
  if (!props.blob) return
  loading.value = true
  error.value = ''
  sheetNames.value = []
  currentSheet.value = ''
  sheetHtml.value = ''

  try {
    const arrayBuffer = await props.blob.arrayBuffer()
    const workbook = XLSX.read(arrayBuffer, { type: 'array' })
    sheetNames.value = workbook.SheetNames
    if (workbook.SheetNames.length > 0) {
      currentSheet.value = workbook.SheetNames[0]
      renderSheet(workbook, workbook.SheetNames[0])
    }
    sheetData.value = workbook
  } catch (e) {
    error.value = e.message || 'Excel 渲染失败'
  } finally {
    loading.value = false
  }
}

function renderSheet(workbook, sheetName) {
  const sheet = workbook.Sheets[sheetName]
  if (!sheet) {
    sheetHtml.value = '<div class="excel-empty">该工作表为空</div>'
    return
  }

  // 获取行列范围用于设置最小宽度
  const ref = sheet['!ref']
  let colCount = 0
  if (ref) {
    const range = XLSX.utils.decode_range(ref)
    colCount = range.e.c - range.s.c + 1
  }

  // 将 sheet 转为 HTML，并去除 SheetJS 自带的 style 标签
  const html = XLSX.utils.sheet_to_html(sheet, {
    id: 'excel-table',
    editable: false,
    header: '',
    footer: '',
  })
  sheetHtml.value = html.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')

  // 根据列数设置最小宽度，确保可滚动
  nextTick(() => {
    const wrapper = tableRef.value
    if (wrapper) {
      const table = wrapper.querySelector('table')
      if (table) {
        const cellWidth = 90 // 每列约 90px
        const minWidth = Math.max(colCount * cellWidth, wrapper.clientWidth)
        table.style.minWidth = minWidth + 'px'
      }
    }
  })
}

function switchSheet(name) {
  if (!sheetData.value || name === currentSheet.value) return
  currentSheet.value = name
  renderSheet(sheetData.value, name)
}

onMounted(renderExcel)
watch(() => props.blob, renderExcel)
</script>

<template>
  <div class="excel-renderer">
    <div v-if="loading" class="excel-loading">
      <div class="loading-spinner"></div>
      <span>正在解析 Excel...</span>
    </div>

    <div v-else-if="error" class="excel-error">{{ error }}</div>

    <div v-else class="excel-container">
      <!-- Sheet tabs -->
      <div v-if="sheetNames.length > 1" class="excel-tabs">
        <button
          v-for="name in sheetNames"
          :key="name"
          class="excel-tab"
          :class="{ active: name === currentSheet }"
          @click="switchSheet(name)"
        >
          {{ name }}
        </button>
      </div>
      <div v-else-if="sheetNames.length === 1" class="excel-sheet-label">
        {{ sheetNames[0] }}
      </div>

      <!-- Table -->
      <div ref="tableRef" class="excel-table-wrapper">
        <div class="excel-table" v-html="sheetHtml"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.excel-renderer {
  min-height: 200px;
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
}

.excel-loading {
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

.excel-error {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80px 24px;
  color: #ef4444;
  font-size: 15px;
}

.excel-container {
  display: flex;
  flex-direction: column;
  min-height: 200px;
  height: 100%;
  width: 100%;
}

/* Sheet tabs */
.excel-tabs {
  display: flex;
  overflow-x: auto;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.excel-tab {
  padding: 8px 20px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-muted);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
  font-family: inherit;
}

.excel-tab:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.excel-tab.active {
  color: var(--accent-primary);
  border-bottom-color: var(--accent-primary);
}

.excel-sheet-label {
  padding: 6px 20px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

/* Table wrapper — 确保能滚动 */
.excel-table-wrapper {
  flex: 1;
  overflow-x: auto;
  overflow-y: auto;
  padding: 0;
  width: 100%;
}

/* SheetJS 生成的内容包裹在 <div id="excel-table"> 中 */
.excel-table {
  font-size: 13px;
}

.excel-table :deep(#excel-table) {
  display: inline-block;
  min-width: 100%;
}

.excel-table :deep(table) {
  border-collapse: collapse;
  width: auto;
  min-width: 100%;
}

.excel-table :deep(td),
.excel-table :deep(th) {
  border: 1px solid var(--border-color);
  padding: 6px 12px;
  text-align: left;
  white-space: nowrap;
  min-width: 80px;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
}

.excel-table :deep(th) {
  background: var(--bg-secondary);
  font-weight: 600;
  position: sticky;
  top: 0;
  z-index: 1;
}

.excel-table :deep(tr:nth-child(even)) {
  background: var(--bg-tertiary);
}

.excel-table :deep(tr:hover) {
  background: rgba(99, 102, 241, 0.06);
}

.excel-empty {
  padding: 60px 24px;
  text-align: center;
  color: var(--text-muted);
  font-size: 15px;
}

@media (max-width: 768px) {
  .excel-tab { padding: 6px 14px; font-size: 12px; }
  .excel-table { font-size: 12px; }
}
</style>