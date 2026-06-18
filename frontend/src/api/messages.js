import client from './client'

export default {
  list(sessionId, params = {}) {
    return client.get(`/messages/${sessionId}`, { params })
  },

  send(sessionId, data) {
    return client.post(`/messages/${sessionId}`, data)
  },

  /**
   * 直接添加一条 assistant 消息（用于前端编排的混合模式等场景持久化汇总消息）
   */
  add(sessionId, data) {
    return client.post(`/messages/${sessionId}/add`, data)
  },

  /**
   * 返回 SSE 流式端点的完整 URL（包含认证 token）
   */
  streamUrl(sessionId) {
    const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:'
    const host = window.location.host
    const token = window.localStorage.getItem('access_token')
    const query = token ? `?token=${encodeURIComponent(token)}` : ''
    return `${protocol}//${host}/api/messages/stream/${sessionId}${query}`
  },
}
