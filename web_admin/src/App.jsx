// web_admin/src/App.jsx
import { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import AdminLayout from './layouts/AdminLayout'
import LoginPage from './pages/login/LoginPage'
import DashboardPage from './pages/dashboard/DashboardPage'
import ChannelsPage from './pages/channels/ChannelsPage'
import SourcesPage from './pages/sources/SourcesPage'
import RtmpPage from './pages/rtmp/RtmpPage'
import LogsPage from './pages/logs/LogsPage'
import TasksPage from './pages/tasks/TasksPage'
import SettingsPage from './pages/settings/SettingsPage'
import AboutPage from './pages/about/AboutPage'
import { getSession } from './api/auth'

const queryClient = new QueryClient()

// 鉴权守卫：未登录重定向登录页
function RequireAuth({ children }) {
  const [state, setState] = useState({ loading: true, logged: false })
  useEffect(() => {
    getSession()
      .then((data) => setState({ loading: false, logged: data.logged_in }))
      .catch(() => setState({ loading: false, logged: false }))
  }, [])
  if (state.loading) return null
  return state.logged ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter basename="/admin">
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<RequireAuth><AdminLayout /></RequireAuth>}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/channels" element={<ChannelsPage />} />
              <Route path="/sources" element={<SourcesPage />} />
              <Route path="/rtmp" element={<RtmpPage />} />
              <Route path="/logs" element={<LogsPage />} />
              <Route path="/tasks" element={<TasksPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/about" element={<AboutPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </QueryClientProvider>
    </ConfigProvider>
  )
}
