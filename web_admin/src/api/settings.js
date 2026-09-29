import request from './client'

export const getSettings = () => request('/api/admin/settings')
export const saveSettings = (items) =>
  request('/api/admin/settings', {
    method: 'PUT',
    body: JSON.stringify({ items }),
  })
