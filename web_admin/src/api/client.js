// 统一请求封装：同源请求自动带 Cookie，401 跳登录
async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    ...options,
  })
  if (res.status === 401) {
    // 登录页等场景的 401 需展示后端具体错误（如“密码错误”），故先解析响应体
    const data401 = await res.json().catch(() => ({}))
    if (!window.location.pathname.endsWith('/login')) {
      window.location.href = '/admin/login'
    }
    throw new Error(data401.error || '未登录或会话已过期')
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(data.error || `请求失败 (${res.status})`)
  }
  return data
}

export default request
