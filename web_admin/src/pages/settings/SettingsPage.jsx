// web_admin/src/pages/settings/SettingsPage.jsx
import { useEffect, useState } from 'react'
import {
  Button, Card, Form, Input, InputNumber, message, Select, Space, Switch,
} from 'antd'
import { useQuery } from '@tanstack/react-query'
import { getSettings, saveSettings } from '../../api/settings'

export default function SettingsPage() {
  const [form] = Form.useForm()
  const { data } = useQuery({ queryKey: ['settings'], queryFn: getSettings })
  const items = data?.items ?? []
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const values = {}
    items.forEach((item) => {
      if (item.kind === 'boolean') values[item.key] = item.value === 'True'
      else if (item.kind === 'integer') values[item.key] = Number(item.value)
      else values[item.key] = item.value
    })
    form.setFieldsValue(values)
  }, [data])

  const onFinish = async (values) => {
    setSaving(true)
    try {
      const payload = items.map((item) => ({
        key: item.key,
        value: String(values[item.key] ?? ''),
      }))
      await saveSettings(payload)
      message.success('已保存，部分配置需重启服务生效')
    } catch (error) {
      message.error(error.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card title="设置">
      <Form form={form} layout="vertical" style={{ maxWidth: 720 }}
            onFinish={onFinish}>
        {items.map((item) => (
          <Form.Item key={item.key} label={item.key} name={item.key}>
            {item.kind === 'boolean' ? <Switch />
              : item.kind === 'integer' ? <InputNumber style={{ width: '100%' }} />
              : item.options?.length ? (
                <Select options={item.options.map((value) => ({ value, label: value }))} />
              ) : <Input />}
          </Form.Item>
        ))}
        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit" loading={saving}>保存</Button>
          </Space>
        </Form.Item>
      </Form>
    </Card>
  )
}
