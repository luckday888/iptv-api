// web_admin/src/pages/logs/LogsPage.jsx
import { useEffect, useRef, useState } from 'react'
import { Button, Card, Input, Select, Space, Switch } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { clearLog, getLog } from '../../api/logs'

const kinds = [
  { value: 'runtime', label: '运行日志' },
  { value: 'result', label: '结果日志' },
  { value: 'speed', label: '测速日志' },
  { value: 'statistics', label: '统计日志' },
  { value: 'unmatch', label: '未匹配日志' },
]

export default function LogsPage() {
  const [kind, setKind] = useState('runtime')
  const [search, setSearch] = useState('')
  const [auto, setAuto] = useState(true)
  const [lines, setLines] = useState([])
  const offsetRef = useRef(0)
  const boxRef = useRef(null)

  const { refetch } = useQuery({
    queryKey: ['log', kind],
    queryFn: () => getLog(kind, 0, search),
    enabled: false,
  })

  // 切换类型/搜索时全量重载
  useEffect(() => {
    let cancelled = false
    setLines([])
    offsetRef.current = 0
    getLog(kind, 0, search).then((data) => {
      if (!cancelled) {
        setLines(data.lines)
        offsetRef.current = data.offset
      }
    })
    return () => { cancelled = true }
  }, [kind, search])

  // 1.5s 增量拉取
  useEffect(() => {
    if (!auto) return undefined
    const timer = setInterval(async () => {
      const data = await getLog(kind, offsetRef.current, '')
      if (data.lines.length) {
        setLines((prev) => [...prev, ...data.lines].slice(-2000))
      }
      offsetRef.current = data.offset
    }, 1500)
    return () => clearInterval(timer)
  }, [auto, kind])

  const onClear = async () => {
    await clearLog(kind)
    setLines([])
    offsetRef.current = 0
  }

  return (
    <Card>
      <Space style={{ marginBottom: 12 }}>
        <Select value={kind} options={kinds} style={{ width: 140 }}
                onChange={setKind} />
        <Input.Search placeholder="搜索" allowClear style={{ width: 220 }}
                      onSearch={setSearch} />
        <Space>
          自动刷新
          <Switch checked={auto} onChange={setAuto} />
        </Space>
        <Button danger onClick={onClear}>清空</Button>
      </Space>
      <div ref={boxRef} style={{
        background: '#1e1e1e', color: '#d4d4d4', padding: 12,
        borderRadius: 6, height: 'calc(100vh - 240px)', overflow: 'auto',
        fontFamily: 'monospace', fontSize: 12, whiteSpace: 'pre-wrap',
      }}>
        {lines.join('\n')}
      </div>
    </Card>
  )
}
