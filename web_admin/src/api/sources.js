import request from './client'

export const getSource = (kind) => request(`/api/admin/sources/${kind}`)
export const saveSource = (kind, raw) =>
  request(`/api/admin/sources/${kind}`, {
    method: 'PUT',
    body: JSON.stringify({ raw }),
  })
