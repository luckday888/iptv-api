import request from './client'

export const getRuntime = () => request('/api/admin/rtmp/runtime')
export const getRtmpChannels = () => request('/api/admin/rtmp/channels')
export const controlStreams = (action, channelKeys) =>
  request('/api/admin/rtmp/streams/control', {
    method: 'POST',
    body: JSON.stringify({ action, channel_keys: channelKeys }),
  })
