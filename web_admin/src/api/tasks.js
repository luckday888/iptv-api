import request from './client'

export const getTasks = (params) => {
  const search = new URLSearchParams(params).toString()
  return request(`/api/admin/tasks?${search}`)
}
