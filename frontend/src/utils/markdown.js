import { marked } from 'marked'
import DOMPurify from 'dompurify'

marked.setOptions({
  breaks: true,
  gfm: true,
})

/**
 * 将助手消息的 Markdown 转为可安全插入页面的 HTML。
 */
export function assistantMarkdownToHtml(text) {
  const s = text == null ? '' : String(text)
  if (!s.trim()) return ''
  const raw = marked.parse(s)
  return DOMPurify.sanitize(raw, { USE_PROFILES: { html: true } })
}
