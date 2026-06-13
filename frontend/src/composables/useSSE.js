/**
 * SSE Composable
 * 管理 Server-Sent Events 连接，用于替代 WebSocket 实现流式响应。
 */
export function useSSE() {
  let eventSource = null
  let handlers = {}

  function connect(url, eventHandlers = {}) {
    disconnect()
    handlers = eventHandlers

    eventSource = new EventSource(url)

    eventSource.onopen = () => {
      console.log('[SSE] 连接已建立')
      handlers.onOpen?.()
    }

    eventSource.onmessage = (event) => {
      // 跳过 keepalive 注释行
      if (event.data === '' || event.data.startsWith(': ')) return
      try {
        const data = JSON.parse(event.data)
        handlers.onMessage?.(data)
      } catch (e) {
        console.warn('[SSE] 解析消息失败:', e)
      }
    }

    eventSource.onerror = () => {
      console.warn('[SSE] 连接错误，将自动重连')
      handlers.onError?.()
    }
  }

  function disconnect() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
  }

  function getReadyState() {
    return eventSource ? eventSource.readyState : EventSource.CLOSED
  }

  return { connect, disconnect, getReadyState }
}