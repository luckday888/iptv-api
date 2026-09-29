// web_admin/src/pages/settings/SettingsPage.jsx
import { useEffect, useState } from 'react'
import {
  Button, Card, Form, Input, InputNumber, message, Select, Space, Switch,
} from 'antd'
import { useQuery } from '@tanstack/react-query'
import { getSettings, saveSettings } from '../../api/settings'

// 后端允许清空（ConfigRule(allow_empty=True)）的 list 配置键，
// 依据 utils/config.py 中 CONFIG_SCHEMA 的实际定义维护
const LIST_ALLOW_EMPTY_KEYS = new Set(['origin_type_prefer'])

// 后端 GET 对 list 项返回 Python list 的 str 形态（如 "['ipv4', 'ipv6']"、空列表为 "[]"），
// 这里将其还原为数组；同时兼容裸逗号串 "ipv4,ipv6"
function parseListValue(raw) {
  if (raw == null) return []
  const text = String(raw).trim()
  if (!text || text === '[]') return []
  // 去掉 Python repr 的方括号后按英文逗号拆分，再剥掉元素两侧引号
  const inner = text.replace(/^\[/, '').replace(/\]$/, '')
  return inner
    .split(',')
    .map((part) => part.trim().replace(/^['"]|['"]$/g, ''))
    .filter(Boolean)
}

// 后端 PUT 校验 list 时按英文逗号拆分（value.split(",")），故提交逗号分隔串
function serializeListValue(value) {
  return Array.isArray(value) ? value.join(',') : ''
}

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
      else if (item.kind === 'list') values[item.key] = parseListValue(item.value)
      else values[item.key] = item.value
    })
    form.setFieldsValue(values)
  }, [data])

  const onFinish = async (values) => {
    setSaving(true)
    try {
      // read_only 项被环境变量锁定，不提交；list 项需序列化为后端接受的逗号串
      const payload = items
        .filter((item) => !item.read_only)
        .map((item) => {
          const formValue = values[item.key]
          const value = item.kind === 'list'
            ? serializeListValue(formValue ?? [])
            : String(formValue ?? '')
          return { key: item.key, value }
        })
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
          <Form.Item
            key={item.key}
            label={item.key}
            name={item.key}
            rules={item.kind === 'list' && !LIST_ALLOW_EMPTY_KEYS.has(item.key)
              ? [{ required: true, message: '至少选择一个值' }]
              : undefined}
          >
            {item.kind === 'boolean' ? <Switch />
              : item.kind === 'integer' ? <InputNumber style={{ width: '100%' }} />
              : item.kind === 'list' ? (
                <Select
                  mode="multiple"
                  allowClear={LIST_ALLOW_EMPTY_KEYS.has(item.key)}
                  options={item.options.map((value) => ({ value, label: value }))}
                />
              )
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
