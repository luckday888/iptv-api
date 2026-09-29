// web_admin/src/pages/channels/ChannelsPage.jsx
import { useState } from 'react'
import {
  Button, Card, Col, Drawer, Input, Layout, List, Popconfirm, Row, Space,
  Table, Tag, message,
} from 'antd'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createChannel, deleteChannels, getCategories, getChannels, getResults,
  retestChannel, screenshotResults,
} from '../../api/channels'

const { Sider, Content } = Layout

export default function ChannelsPage() {
  const queryClient = useQueryClient()
  const [category, setCategory] = useState()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState()
  const [selectedRows, setSelectedRows] = useState([])

  const { data: categories = [] } = useQuery({
    queryKey: ['channel-categories'], queryFn: getCategories,
  })
  const { data: channelPage } = useQuery({
    queryKey: ['channels', category, search, page],
    queryFn: () => getChannels({
      category: category || '', search, page, page_size: 50,
    }),
  })
  const { data: results = [] } = useQuery({
    queryKey: ['channel-results', selected?.channel_key],
    queryFn: () => getResults(selected.channel_key),
    enabled: !!selected,
  })

  const onCreate = async () => {
    const name = window.prompt('频道名')
    if (name) {
      await createChannel('自定义', name)
      queryClient.invalidateQueries()
    }
  }

  const onDelete = async () => {
    await deleteChannels(selectedRows.map((row) => row.channel_key))
    message.success('已删除')
    queryClient.invalidateQueries()
    setSelectedRows([])
  }

  const columns = [
    { title: '频道', dataIndex: 'name' },
    { title: '接口总数', dataIndex: 'total_results', width: 90 },
    { title: '待测', dataIndex: 'untested_results', width: 80 },
    { title: '有效', dataIndex: 'valid_results', width: 80 },
    { title: '已选', dataIndex: 'selected_results', width: 80 },
    {
      title: '最高分辨率', dataIndex: 'max_resolution', width: 120,
      render: (value) => value || '-',
    },
  ]

  return (
    <Layout>
      <Sider width={200} theme="light" style={{ padding: 8 }}>
        <List size="small"
              dataSource={[{ category: '', channel_count: undefined }, ...categories]}
              renderItem={(item) => (
            <List.Item style={{
              cursor: 'pointer',
              background: (category || '') === item.category ? '#e6f4ff' : undefined,
              padding: '6px 8px',
            }}
              onClick={() => { setCategory(item.category || undefined); setPage(1) }}>
              {item.category ? `${item.category} (${item.channel_count})` : '全部分类'}
            </List.Item>
          )} />
      </Sider>
      <Content style={{ paddingLeft: 16 }}>
        <Space style={{ marginBottom: 12 }}>
          <Input.Search placeholder="搜索频道" allowClear
            style={{ width: 240 }}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }} />
          <Button onClick={onCreate}>新增频道</Button>
          <Popconfirm title="确认删除选中频道？" onConfirm={onDelete}
                      disabled={!selectedRows.length}>
            <Button danger disabled={!selectedRows.length}>删除</Button>
          </Popconfirm>
        </Space>
        <Table rowKey="channel_key" columns={columns}
               dataSource={channelPage?.items ?? []}
               onRow={(record) => ({ onClick: () => setSelected(record) })}
               rowSelection={{
                 selectedRowKeys: selectedRows.map((row) => row.channel_key),
                 onChange: (_keys, rows) => setSelectedRows(rows),
               }}
          pagination={{
            current: page, pageSize: 50, total: channelPage?.total ?? 0,
            showSizeChanger: false, onChange: setPage,
          }} />
      </Content>

      <Drawer title={selected?.name} open={!!selected} width={560}
              onClose={() => setSelected(undefined)}>
        <Space style={{ marginBottom: 12 }}>
          <Button onClick={async () => {
            await retestChannel(selected.channel_key)
            message.info('已发起频道重测')
          }}>频道重测</Button>
          <Button onClick={async () => {
            await screenshotResults(selected.channel_key,
              results.map((row) => row.result_key))
            message.info('已发起截图')
          }}>全部截图</Button>
        </Space>
        <Table rowKey="result_key" pagination={false} dataSource={results}
               columns={[
                 { title: 'URL', dataIndex: 'url', ellipsis: true },
                 { title: '来源', dataIndex: 'origin', width: 90 },
                 {
                   title: '有效', dataIndex: 'valid', width: 70,
                   render: (valid) => <Tag color={valid ? 'green' : 'red'}>{valid ? '是' : '否'}</Tag>,
                 },
                 { title: '速度', dataIndex: 'speed', width: 90,
                   render: (value) => (value ? Number(value).toFixed(2) : '-') },
                 { title: '分辨率', dataIndex: 'resolution', width: 110 },
               ]} />
      </Drawer>
    </Layout>
  )
}
