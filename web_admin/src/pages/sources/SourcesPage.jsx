// web_admin/src/pages/sources/SourcesPage.jsx
import { useEffect, useState } from 'react'
import { Button, Card, Space, Tabs, Input, message } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { getSource, saveSource } from '../../api/sources'

const tabs = [
  { key: 'template', label: '模板' },
  { key: 'local', label: '本地源' },
  { key: 'subscribe', label: '订阅' },
  { key: 'epg', label: 'EPG' },
  { key: 'whitelist', label: '白名单' },
  { key: 'blacklist', label: '黑名单' },
  { key: 'alias', label: '别名' },
]

function SourceEditor({ kind }) {
  const { data } = useQuery({
    queryKey: ['source', kind], queryFn: () => getSource(kind),
  })
  const [text, setText] = useState('')
  const [dirty, setDirty] = useState(false)

  useEffect(() => {
    setText(data?.raw ?? '')
    setDirty(false)
  }, [data?.raw])

  // 离开页面前提醒未保存内容
  useEffect(() => {
    const handler = (event) => {
      if (dirty) event.preventDefault()
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [dirty])

  const onSave = async () => {
    await saveSource(kind, text)
    setDirty(false)
    message.success('已保存')
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Space>
        <Button type="primary" onClick={onSave} disabled={!dirty}>保存</Button>
        <span style={{ color: '#999' }}>{data?.path}</span>
      </Space>
      <Input.TextArea value={text} rows={22} spellCheck={false}
                      style={{ fontFamily: 'monospace' }}
                      onChange={(e) => { setText(e.target.value); setDirty(true) }} />
    </Space>
  )
}

export default function SourcesPage() {
  return (
    <Card>
      <Tabs items={tabs.map((tab) => ({
        key: tab.key,
        label: tab.label,
        children: <SourceEditor key={tab.key} kind={tab.key} />,
      }))} />
    </Card>
  )
}
