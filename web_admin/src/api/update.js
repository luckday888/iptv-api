import request from './client'

export const getProgress = () => request('/api/admin/update/progress')
const action = (path) => () => request(`/api/admin/update/${path}`, { method: 'POST' })
export const runUpdate = action('run')
export const pauseUpdate = action('pause')
export const resumeUpdate = action('resume')
export const cancelUpdate = action('cancel')
