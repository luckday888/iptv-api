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
