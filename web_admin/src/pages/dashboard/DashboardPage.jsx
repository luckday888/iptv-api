import { useState } from 'react'
import {
  Button, Card, Col, Progress, Row, Statistic, Table, Input, Space, Tag,
} from 'antd'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getDashboardChannels, getMetrics,
} from '../../api/dashboard'
import {
  cancelUpdate, getProgress, pauseUpdate, resumeUpdate, runUpdate,
} from '../../api/update'

const healthColor = {
  healthy: 'green', warning: 'gold', offline: 'red', unknown: 'default',
}

export default function DashboardPage() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')

  // 指标：5s 轮询
  const { data: metrics } = useQuery({
    queryKey: ['dashboard-metrics'],
    queryFn: getMetrics,
    refetchInterval: 5000,
  })

  // 进度：运行中 1s，空闲时不轮询
  const { data: progress } = useQuery({
    queryKey: ['update-progress'],
    queryFn: getProgress,
    refetchInterval: (query) =>
      query.state.data?.status === 'idle' ? false : 1000,
  })

  const { data: channelPage } = useQuery({
    queryKey: ['dashboard-channels', page, search],
    queryFn: () => getDashboardChannels({
      page, page_size: 20, search,
    }),
  })

  const refresh = () => queryClient.invalidateQueries()
  const mutationOptions = { onSuccess: refresh }
  const runM = useMutation({ mutationFn: runUpdate, ...mutationOptions })
  const pauseM = useMutation({ mutationFn: pauseUpdate, ...mutationOptions })
  const resumeM = useMutation({ mutationFn: resumeUpdate, ...mutationOptions })
  const cancelM = useMutation({ mutationFn: cancelUpdate, ...mutationOptions })

  const running = progress?.status === 'running' || progress?.status === 'paused'

  const columns = [
    { title: '分类', dataIndex: 'category', width: 120 },
    { title: '频道', dataIndex: 'name' },
    {
      title: '健康度', dataIndex: 'health', width: 100,
      render: (health) => <Tag color={healthColor[health] || 'default'}>{health}</Tag>,
    },
    { title: '接口总数', dataIndex: 'total_results', width: 90 },
    { title: '有效数', dataIndex: 'valid_results', width: 80 },
  ]

  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Row gutter={16}>
        <Col span={8}>
          <Card><Statistic title="频道总数" value={metrics?.channel_total ?? 0} /></Card>
        </Col>
        <Col span={8}>
          <Card><Statistic title="有效接口" value={metrics?.valid_total ?? 0} /></Card>
        </Col>
        <Col span={8}>
          <Card><Statistic title="运行状态" value={metrics?.run_status ?? '-'} /></Card>
        </Col>
      </Row>

      <Card title="更新进度">
        <Progress percent={progress?.percent ?? 0} />
        <div style={{ marginBottom: 12 }}>{progress?.title}</div>
        <Space>
          {running ? (
            <>
              {progress?.status === 'paused' ? (
                <Button onClick={() => resumeM.mutate()}>继续</Button>
              ) : (
                <Button onClick={() => pauseM.mutate()}>暂停</Button>
              )}
              <Button danger onClick={() => cancelM.mutate()}>取消</Button>
            </>
          ) : (
            <Button type="primary" onClick={() => runM.mutate()}>执行更新</Button>
          )}
        </Space>
      </Card>

      <Card title="频道结果">
        <Input.Search placeholder="搜索分类/频道" allowClear style={{ width: 260 }}
                      onChange={(e) => { setSearch(e.target.value); setPage(1) }} />
        <Table rowKey="channel_key" columns={columns} style={{ marginTop: 12 }}
               dataSource={channelPage?.items ?? []}
               pagination={{
                 current: page, pageSize: 20, total: channelPage?.total ?? 0,
                 showSizeChanger: false, onChange: setPage,
               }} />
      </Card>
    </Space>
  )
}
