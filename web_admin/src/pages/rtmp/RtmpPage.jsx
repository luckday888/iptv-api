// web_admin/src/pages/rtmp/RtmpPage.jsx
import { useEffect, useState } from 'react'
import {
  Button, Card, Col, Modal, Row, Space, Statistic, Table, Tag, message,
} from 'antd'
import { Line } from '@ant-design/plots'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  controlStreams, getRtmpChannels, getRuntime,
} from '../../api/rtmp'

export default function RtmpPage() {
  const queryClient = useQueryClient()
  const [pickerOpen, setPickerOpen] = useState(false)
  const [picked, setPicked] = useState([])
  const [history, setHistory] = useState([])

  // 运行时 2s 轮询
  const { data: runtime } = useQuery({
    queryKey: ['rtmp-runtime'], queryFn: getRuntime, refetchInterval: 2000,
  })
  const { data: channels = [] } = useQuery({
    queryKey: ['rtmp-channels'], queryFn: getRtmpChannels,
  })

  // 累积带宽采样点用于曲线图，仅保留最近 60 个
  useEffect(() => {
    if (runtime?.sampled_at) {
      setHistory((prev) => [
        ...prev.slice(-60),
        { time: new Date(runtime.sampled_at * 1000).toLocaleTimeString(),
          bw: Number(runtime.bw_out || 0) },
      ])
    }
  }, [runtime?.sampled_at])

  const controlM = useMutation({
    mutationFn: ({ action, keys }) => controlStreams(action, keys),
    onSuccess: () => queryClient.invalidateQueries(),
  })

  const onStart = async () => {
    const result = await controlM.mutateAsync({ action: 'start', keys: picked })
    message[result.errors.length ? 'warning' : 'success'](
      `成功 ${result.success}/${result.total}`)
    setPickerOpen(false)
    setPicked([])
  }

  const columns = [
    { title: '频道', dataIndex: 'channel_name' },
    { title: '客户端数', dataIndex: 'clients', width: 90 },
    { title: '分辨率', dataIndex: 'resolution', width: 110 },
    {
      title: '带宽(kbps)', dataIndex: 'bw_out', width: 110,
      render: (value) => Number(value || 0).toFixed(0),
    },
    {
      title: '运行(秒)', dataIndex: 'uptime', width: 90,
      render: (value) => Math.round(Number(value || 0)),
    },
    {
      title: '操作', width: 90,
      render: (_, record) => (
        <Button size="small" danger
          onClick={() => controlM.mutate({
            action: 'stop', keys: [record.channel_key || record.result_key],
          })}>
          停止
        </Button>
      ),
    },
  ]

  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Row gutter={16}>
        <Col span={6}>
          <Card><Statistic title="活动转推" value={runtime?.active_count ?? 0} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="启动中" value={runtime?.starting_count ?? 0} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="可用槽位" value={runtime?.available_slots ?? 0} /></Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="状态"
              valueStyle={{ fontSize: 18 }}
              value={runtime?.available ? runtime.status : '不可用'}
              prefix={runtime?.available ? <Tag color="green">在线</Tag> : <Tag>离线</Tag>} />
          </Card>
        </Col>
      </Row>

      <Card title="总带宽曲线 (kbps)">
        <Line data={history} xField="time" yField="bw" height={180}
              smooth animation={false} />
      </Card>

      <Card title="转推列表" extra={
        <Button type="primary" onClick={() => setPickerOpen(true)}>发起转推</Button>
      }>
        <Table rowKey="result_key" columns={columns}
               dataSource={runtime?.streams ?? []} pagination={false} />
      </Card>

      <Modal title="选择频道" open={pickerOpen} onOk={onStart}
             onCancel={() => setPickerOpen(false)}>
        <Table rowKey="channel_key" size="small" dataSource={channels}
               rowSelection={{
                 selectedRowKeys: picked,
                 onChange: (keys) => setPicked(keys),
               }}
          columns={[
            { title: '频道', dataIndex: 'channel_name' },
            { title: '分类', dataIndex: 'category', width: 120 },
          ]} />
      </Modal>
    </Space>
  )
}
