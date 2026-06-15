<script setup>
import { computed } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'

// 配置 marked 使用 highlight.js
marked.setOptions({
  gfm: true,
  breaks: true,
  highlight(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(code, { language: lang }).value
      } catch (_) {}
    }
    try {
      return hljs.highlightAuto(code).value
    } catch (_) {}
    return code
  },
})

const props = defineProps({
  content: { type: String, default: '' },
})

const renderedHtml = computed(() => {
  if (!props.content) return ''
  try {
    return marked.parse(props.content)
  } catch (e) {
    return `<p>Markdown 渲染失败: ${e.message}</p>`
  }
})
</script>

<template>
  <div class="markdown-renderer" v-html="renderedHtml"></div>
</template>

<style scoped>
.markdown-renderer {
  padding: 28px 36px;
  font-size: 15px;
  line-height: 1.8;
  color: var(--text-primary);
  max-width: 100%;
}

.markdown-renderer :deep(h1),
.markdown-renderer :deep(h2),
.markdown-renderer :deep(h3),
.markdown-renderer :deep(h4),
.markdown-renderer :deep(h5),
.markdown-renderer :deep(h6) {
  margin-top: 1.8em;
  margin-bottom: 0.6em;
  font-weight: 700;
  line-height: 1.3;
  color: var(--text-primary);
}

.markdown-renderer :deep(h1) { font-size: 1.7em; border-bottom: 1px solid var(--border-color); padding-bottom: 0.3em; }
.markdown-renderer :deep(h2) { font-size: 1.4em; border-bottom: 1px solid var(--border-color); padding-bottom: 0.25em; }
.markdown-renderer :deep(h3) { font-size: 1.2em; }
.markdown-renderer :deep(h4) { font-size: 1.1em; }

.markdown-renderer :deep(p) {
  margin: 0.8em 0;
}

.markdown-renderer :deep(code) {
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 0.88em;
  padding: 2px 7px;
  border-radius: 4px;
  background: var(--bg-tertiary);
  color: var(--accent-primary);
}

.markdown-renderer :deep(pre) {
  background: #1e1e2e;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 18px 22px;
  overflow-x: auto;
  margin: 1.2em 0;
}

.markdown-renderer :deep(pre code) {
  padding: 0;
  background: none;
  color: inherit;
  font-size: 13px;
  line-height: 1.7;
}

.markdown-renderer :deep(blockquote) {
  margin: 1em 0;
  padding: 8px 16px;
  border-left: 3px solid var(--accent-primary);
  background: var(--bg-secondary);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  color: var(--text-secondary);
}

.markdown-renderer :deep(a) {
  color: var(--accent-primary);
  text-decoration: none;
  font-weight: 500;
}

.markdown-renderer :deep(a:hover) {
  text-decoration: underline;
}

.markdown-renderer :deep(ul),
.markdown-renderer :deep(ol) {
  padding-left: 1.6em;
  margin: 0.6em 0;
}

.markdown-renderer :deep(li) {
  margin: 0.3em 0;
}

.markdown-renderer :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 1em 0;
  font-size: 14px;
}

.markdown-renderer :deep(th),
.markdown-renderer :deep(td) {
  border: 1px solid var(--border-color);
  padding: 8px 12px;
  text-align: left;
}

.markdown-renderer :deep(th) {
  background: var(--bg-secondary);
  font-weight: 600;
}

.markdown-renderer :deep(tr:nth-child(even)) {
  background: var(--bg-tertiary);
}

.markdown-renderer :deep(strong) {
  font-weight: 700;
}

.markdown-renderer :deep(img) {
  max-width: 100%;
  border-radius: var(--radius-md);
  margin: 1em 0;
}

.markdown-renderer :deep(hr) {
  border: none;
  border-top: 1px solid var(--border-color);
  margin: 1.5em 0;
}

@media (max-width: 768px) {
  .markdown-renderer {
    padding: 20px 24px;
    font-size: 14px;
  }
}

@media (max-width: 480px) {
  .markdown-renderer {
    padding: 16px 16px;
    font-size: 13px;
  }
}
</style>