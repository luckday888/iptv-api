import request from './client'

export const getCategories = () => request('/api/admin/channels/categories')

export const getChannels = (params) => {
  const search = new URLSearchParams(params).toString()
  return request(`/api/admin/channels?${search}`)
}

export const getResults = (channelKey) =>
  request(`/api/admin/channels/${channelKey}/results`)

export const deleteChannels = (channelKeys) =>
  request('/api/admin/channels', {
    method: 'DELETE',
    body: JSON.stringify({ channel_keys: channelKeys }),
  })

export const createChannel = (category, name) =>
  request('/api/admin/channels', {
    method: 'POST',
    body: JSON.stringify({ category, name }),
  })

// 频道操作（异步，进度经任务历史/操作状态反映）
const postAction = (path) => () =>
  request(`/api/admin/channels/${path}`, { method: 'POST' })

export const retestChannel = (channelKey) => postAction(`${channelKey}/retest`)()

export const retestResults = (channelKey, resultKeys) =>
  request(`/api/admin/channels/${channelKey}/results/retest`, {
    method: 'POST',
    body: JSON.stringify({ result_keys: resultKeys }),
  })

export const screenshotResults = (channelKey, resultKeys) =>
  request(`/api/admin/channels/${channelKey}/results/screenshot`, {
    method: 'POST',
    body: JSON.stringify({ result_keys: resultKeys }),
  })
