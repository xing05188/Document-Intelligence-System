import client from './client'

const TOKEN_KEY = 'access_token'

function setAccessToken(token) {
  if (token) {
    window.localStorage.setItem(TOKEN_KEY, token)
  }
}

function clearAccessToken() {
  window.localStorage.removeItem(TOKEN_KEY)
}

export function getAccessToken() {
  return window.localStorage.getItem(TOKEN_KEY)
}

/**
 * 直接解析 JWT token 获取用户信息，避免 /api/auth/me 调用
 * JWT 格式: base64url(payload).base64url(signature)
 */
function parseJwtPayload(token) {
  try {
    const parts = token.split('.')
    if (parts.length !== 2) return null
    let payload = parts[0]
    const padding = '='.repeat((4 - (payload.length % 4)) % 4)
    payload = (payload + padding).replace(/-/g, '+').replace(/_/g, '/')
    const decoded = JSON.parse(window.atob(payload))
    return decoded
  } catch {
    return null
  }
}

/**
 * 从本地 token 快速获取用户信息（不发起网络请求）
 */
export function getUserFromToken() {
  const token = getAccessToken()
  if (!token) return null
  const payload = parseJwtPayload(token)
  if (!payload) return null
  // 检查 token 是否过期
  const exp = payload.exp
  if (exp && Date.now() / 1000 > exp) {
    return null
  }
  return {
    id: payload.sub,
    phone: payload.phone,
    display_name: payload.display_name,
    status: payload.status || 'active',
  }
}

export default {
  register(data) {
    return client.post('/auth/register', data).then((res) => {
      if (res?.access_token) {
        setAccessToken(res.access_token)
      }
      return res
    })
  },

  login(data) {
    return client.post('/auth/login', data).then((res) => {
      if (res?.access_token) {
        setAccessToken(res.access_token)
      }
      return res
    })
  },

  me() {
    return client.get('/auth/me')
  },

  logout() {
    return client.post('/auth/logout').finally(() => {
      clearAccessToken()
    })
  },

  clearAccessToken,
  setAccessToken,
}