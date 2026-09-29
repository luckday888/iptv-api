// web_admin/src/pages/about/AboutPage.jsx
import { Button, Card, Descriptions, Space, Typography, message } from 'antd'
import { useQuery } from '@tanstack/react-query'
import {
  checkUpdate, getChangelog, getVersion,
} from '../../api/about'

export default function AboutPage() {
  const { data: version } = useQuery({
    queryKey: ['about-version'], queryFn: getVersion,
  })
  const { data: changelog } = useQuery({
    queryKey: ['about-changelog'], queryFn: getChangelog,
  })

  const onCheck = async () => {
    const result = await checkUpdate()
    result.has_update
      ? message.info(`发现新版本 ${result.latest}`)
      : message.success('当前已是最新版本')
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Card>
        <Descriptions column={1} title={version?.name}>
          <Descriptions.Item label="版本">{version?.version}</Descriptions.Item>
          <Descriptions.Item label="作者">{version?.author}</Descriptions.Item>
          <Descriptions.Item label="仓库">
            <Typography.Link href={version?.repository} target="_blank">
              {version?.repository}
            </Typography.Link>
          </Descriptions.Item>
          <Descriptions.Item>
            <Button type="primary" onClick={onCheck}>检查更新</Button>
          </Descriptions.Item>
        </Descriptions>
      </Card>
      <Card title="更新日志">
        <pre style={{ whiteSpace: 'pre-wrap' }}>{changelog?.content}</pre>
      </Card>
    </Space>
  )
}
