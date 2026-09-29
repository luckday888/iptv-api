import { useEffect } from 'react'
import { getSession } from './api/auth'

export default function App() {
  useEffect(() => {
    getSession().catch(() => {})
  }, [])
  return <div>IPTV-API 管理端</div>
}
