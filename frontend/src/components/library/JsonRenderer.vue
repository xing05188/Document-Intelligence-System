<script setup>
import { computed } from 'vue'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'

const props = defineProps({
  content: { type: String, default: '' },
})

const renderedHtml = computed(() => {
  if (!props.content) return ''
  // 尝试格式化 JSON
  let raw = props.content
  try {
    const parsed = JSON.parse(raw)
    raw = JSON.stringify(parsed, null, 2)
  } catch (_) {
    // 非合法 JSON，直接显示原文
  }
  try {
    return hljs.highlight(raw, { language: 'json' }).value
  } catch (_) {
    return `<pre>${raw}</pre>`
  }
})
</script>

<template>
  <div class="json-renderer">
    <div class="json-toolbar">
      <span class="json-label">JSON</span>
      <button
        class="json-copy-btn"
        type="button"
        @click="copyContent"
      >{{ copyLabel }}</button>
    </div>
    <pre class="json-content" v-html="renderedHtml"></pre>
  </div>
</template>

<script>
export default {
  data() {
    return { copyLabel: '复制' }
  },
  methods: {
    copyContent() {
      let raw = this.content
      try {
        raw = JSON.stringify(JSON.parse(raw), null, 2)
      } catch (_) {}
      navigator.clipboard.writeText(raw).then(() => {
        this.copyLabel = '已复制'
        setTimeout(() => { this.copyLabel = '复制' }, 2000)
      })
    }
  }
}
</script>

<style scoped>
.json-renderer {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.json-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 20px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
  flex-shrink: 0;
}

.json-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.json-copy-btn {
  padding: 4px 12px;
  font-size: 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-primary);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.json-copy-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.json-content {
  flex: 1;
  min-height: 0;
  margin: 0;
  padding: 20px 24px;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.7;
  overflow: auto;
  background: #1e1e2e;
  color: #cdd6f4;
}

.json-content :deep(.hljs) {
  background: transparent;
  padding: 0;
}
</style>