// web_admin/src/layouts/AdminLayout.jsx
import { Layout, Menu, Button } from 'antd'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { logout } from '../api/auth'

const { Header, Sider, Content } = Layout

const items = [
  { key: '/dashboard', label: '仪表盘' },
  { key: '/channels', label: '频道中心' },
  { key: '/sources', label: '订阅源' },
  { key: '/rtmp', label: '播放转推' },
  { key: '/logs', label: '日志' },
  { key: '/tasks', label: '任务历史' },
  { key: '/settings', label: '设置' },
  { key: '/about', label: '关于' },
]

export default function AdminLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const selected = items.find((item) => location.pathname.startsWith(item.key))

  const onLogout = async () => {
    await logout().catch(() => {})
    navigate('/login')
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider theme="light">
        <Menu mode="inline" selectedKeys={selected ? [selected.key] : []}
              items={items}
              onClick={({ key }) => navigate(key)} />
      </Sider>
      <Layout>
        <Header style={{ background: '#fff', display: 'flex',
                        justifyContent: 'flex-end', alignItems: 'center' }}>
          <Button onClick={onLogout}>退出登录</Button>
        </Header>
        <Content style={{ margin: 16 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
