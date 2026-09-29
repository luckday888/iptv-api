import request from './client'

export const getLog = (kind, offset = 0, search = '') => {
  const params = new URLSearchParams({ offset, search }).toString()
  return request(`/api/admin/logs/${kind}?${params}`)
}
export const clearLog = (kind) =>
  request(`/api/admin/logs/${kind}`, { method: 'DELETE' })
