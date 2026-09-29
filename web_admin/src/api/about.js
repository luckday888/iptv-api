import request from './client'

export const getVersion = () => request('/api/admin/about/version')
export const checkUpdate = () => request('/api/admin/about/update-check')
export const getChangelog = () => request('/api/admin/about/changelog')
