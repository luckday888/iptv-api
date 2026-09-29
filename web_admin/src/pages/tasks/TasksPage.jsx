// web_admin/src/pages/tasks/TasksPage.jsx
import { useState } from 'react'
import { Card, Table, Tag } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { getTasks } from '../../api/tasks'

const statusColor = {
  success: 'green', running: 'blue', failed: 'red',
}

export default function TasksPage() {
  const [page, setPage] = useState(1)
  const { data } = useQuery({
    queryKey: ['tasks', page],
    queryFn: () => getTasks({ page, page_size: 50 }),
    refetchInterval: 3000,
  })

  const columns = [
    {
      title: '来源', dataIndex: 'source', width: 100,
      render: (source) => source === 'run' ? '完整更新' : '频道操作',
    },
    { title: '任务', dataIndex: 'task', width: 160 },
    { title: '目标', dataIndex: 'target' },
    {
      title: '状态', dataIndex: 'status', width: 100,
      render: (status) => <Tag color={statusColor[status] || 'default'}>{status}</Tag>,
    },
    {
      title: '耗时(秒)', dataIndex: 'duration', width: 100,
      render: (value) => (value == null ? '-' : Number(value).toFixed(1)),
    },
    { title: '详情', dataIndex: 'details', ellipsis: true },
  ]

  return (
    <Card title="任务历史">
      <Table rowKey="id" columns={columns} dataSource={data?.items ?? []}
             pagination={{
               current: page, pageSize: 50, total: data?.total ?? 0,
               showSizeChanger: false, onChange: setPage,
             }} />
    </Card>
  )
}
