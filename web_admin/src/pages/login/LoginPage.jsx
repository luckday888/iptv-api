// web_admin/src/pages/login/LoginPage.jsx
import { useState } from 'react'
import { Button, Card, Form, Input, message } from 'antd'
import { useNavigate } from 'react-router-dom'
import { login } from '../../api/auth'

export default function LoginPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)

  const onFinish = async ({ password }) => {
    setLoading(true)
    try {
      await login(password)
      navigate('/dashboard')
    } catch (error) {
      message.error(error.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex',
                  alignItems: 'center', justifyContent: 'center' }}>
      <Card title="IPTV-API 管理端" style={{ width: 360 }}>
        <Form onFinish={onFinish}>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password placeholder="管理密码" autoFocus />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading}>
              登录
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}
