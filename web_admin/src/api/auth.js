import request from './client'

export function getSession() {
  return request('/api/admin/auth/session')
}

export function login(password) {
  return request('/api/admin/auth/login', {
    method: 'POST',
    body: JSON.stringify({ password }),
  })
}

export function logout() {
  return request('/api/admin/auth/logout', { method: 'POST' })
}

// 修改管理密码：校验旧密码，成功后旧会话立即失效
export function changePassword(oldPassword, newPassword) {
  return request('/api/admin/auth/password', {
    method: 'PUT',
    body: JSON.stringify({
      old_password: oldPassword,
      new_password: newPassword,
    }),
  })
}
