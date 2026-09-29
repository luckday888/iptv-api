import request from './client'

export const getMetrics = () => request('/api/admin/dashboard/metrics')

export const getDashboardChannels = (params) => {
  const search = new URLSearchParams(params).toString()
  return request(`/api/admin/dashboard/channels?${search}`)
}
