import { useState, useEffect } from 'react'
import { Routes, Route, Navigate, Link, useLocation } from 'react-router-dom'
import { Toaster } from '@/components/ui/toaster'
import { useToast } from '@/hooks/use-toast'
import { useAuth } from '@/contexts/AuthContext'
import HomePage from './pages/HomePage'
import TradeLogsPage from './pages/TradeLogsPage'
import SettingsPage from './pages/SettingsPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import { Moon, Sun, Home, FileText, Settings, LogOut } from 'lucide-react'
import { Button } from '@/components/ui/button'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export interface SystemStatus {
  api_configured: boolean
  exchange: string
  connected: boolean
  connection_message: string
  auto_trading_enabled: boolean
  webhook_url: string
  last_webhook: any
  last_order: any
  current_position: any
  current_pnl: number
  total_pnl: number
  total_trades: number
  settings: {
    trading_mode: string
    slippage: number
    stop_loss_percent: number
    take_profit_percent: number
    default_position_size: number
  }
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()
  
  if (isLoading) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  
  return <>{children}</>
}

function MainLayout() {
  const [darkMode, setDarkMode] = useState(false)
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null)
  const { toast } = useToast()
  const { token, logout, user } = useAuth()
  const location = useLocation()

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [darkMode])

  useEffect(() => {
    if (token) {
      fetchSystemStatus()
      const interval = setInterval(fetchSystemStatus, 5000)
      return () => clearInterval(interval)
    }
  }, [token])

  const fetchSystemStatus = async () => {
    if (!token) return
    
    try {
      const response = await fetch(`${API_URL}/system-status`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.status === 401) {
        logout()
        return
      }
      
      const data = await response.json()
      setSystemStatus(data)
    } catch (error) {
      console.error('Failed to fetch system status:', error)
    }
  }

  const toggleDarkMode = () => {
    setDarkMode(!darkMode)
  }

  const handleLogout = () => {
    logout()
    toast({
      title: 'Logged out',
      description: 'You have been logged out successfully',
    })
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 transition-colors duration-300">
      <nav className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-8">
              <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                SignalTrader
              </h1>
              <div className="hidden md:flex space-x-4">
                <Link to="/">
                  <Button
                    variant={location.pathname === '/' ? 'default' : 'ghost'}
                    className="flex items-center space-x-2"
                  >
                    <Home className="w-4 h-4" />
                    <span>Home</span>
                  </Button>
                </Link>
                <Link to="/logs">
                  <Button
                    variant={location.pathname === '/logs' ? 'default' : 'ghost'}
                    className="flex items-center space-x-2"
                  >
                    <FileText className="w-4 h-4" />
                    <span>Trade Logs</span>
                  </Button>
                </Link>
                <Link to="/settings">
                  <Button
                    variant={location.pathname === '/settings' ? 'default' : 'ghost'}
                    className="flex items-center space-x-2"
                  >
                    <Settings className="w-4 h-4" />
                    <span>Settings</span>
                  </Button>
                </Link>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              {user && (
                <span className="text-sm text-slate-600 dark:text-slate-400 hidden md:block">
                  {user.username}
                </span>
              )}
              <Button
                variant="outline"
                size="icon"
                onClick={toggleDarkMode}
                className="rounded-full"
              >
                {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
              </Button>
              <Button
                variant="outline"
                size="icon"
                onClick={handleLogout}
                className="rounded-full"
              >
                <LogOut className="w-5 h-5" />
              </Button>
            </div>
          </div>
        </div>
      </nav>

      <div className="md:hidden bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
        <div className="flex justify-around p-2">
          <Link to="/" className="flex-1 mx-1">
            <Button
              variant={location.pathname === '/' ? 'default' : 'ghost'}
              className="w-full"
            >
              <Home className="w-4 h-4" />
            </Button>
          </Link>
          <Link to="/logs" className="flex-1 mx-1">
            <Button
              variant={location.pathname === '/logs' ? 'default' : 'ghost'}
              className="w-full"
            >
              <FileText className="w-4 h-4" />
            </Button>
          </Link>
          <Link to="/settings" className="flex-1 mx-1">
            <Button
              variant={location.pathname === '/settings' ? 'default' : 'ghost'}
              className="w-full"
            >
              <Settings className="w-4 h-4" />
            </Button>
          </Link>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Routes>
          <Route path="/" element={
            <ProtectedRoute>
              <HomePage
                systemStatus={systemStatus}
                onStatusUpdate={fetchSystemStatus}
                apiUrl={API_URL}
                toast={toast}
                token={token!}
              />
            </ProtectedRoute>
          } />
          <Route path="/logs" element={
            <ProtectedRoute>
              <TradeLogsPage apiUrl={API_URL} token={token!} />
            </ProtectedRoute>
          } />
          <Route path="/settings" element={
            <ProtectedRoute>
              <SettingsPage
                systemStatus={systemStatus}
                onStatusUpdate={fetchSystemStatus}
                apiUrl={API_URL}
                toast={toast}
                token={token!}
              />
            </ProtectedRoute>
          } />
        </Routes>
      </main>

      <Toaster />
    </div>
  )
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/*" element={<MainLayout />} />
    </Routes>
  )
}

export default App
