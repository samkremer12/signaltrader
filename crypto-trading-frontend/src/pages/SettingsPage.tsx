import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { CheckCircle2, XCircle, AlertTriangle } from 'lucide-react'
import { SystemStatus } from '../App'

interface SettingsPageProps {
  systemStatus: SystemStatus | null
  onStatusUpdate: () => void
  apiUrl: string
  toast: any
  token: string
}

export default function SettingsPage({ systemStatus, onStatusUpdate, apiUrl, toast, token }: SettingsPageProps) {
  const [exchange, setExchange] = useState('binance')
  const [tradingMode, setTradingMode] = useState('market')
  const [slippage, setSlippage] = useState('0.5')
  const [stopLoss, setStopLoss] = useState('2.0')
  const [takeProfit, setTakeProfit] = useState('5.0')
  const [positionSize, setPositionSize] = useState('100')
  const [saving, setSaving] = useState(false)
  const [diagnostics, setDiagnostics] = useState<any>(null)
  const [runningDiagnostics, setRunningDiagnostics] = useState(false)
  
  // Phase 2 settings
  const [paperTradingEnabled, setPaperTradingEnabled] = useState(false)
  const [trailingStopEnabled, setTrailingStopEnabled] = useState(false)
  const [trailingStopPercent, setTrailingStopPercent] = useState('1.0')
  const [notificationsEnabled, setNotificationsEnabled] = useState(false)
  const [notificationEmail, setNotificationEmail] = useState('')
  const [tieredTpEnabled, setTieredTpEnabled] = useState(false)

  useEffect(() => {
    // Fetch settings from backend on mount
    const fetchSettings = async () => {
      try {
        const response = await fetch(`${apiUrl}/settings`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        const data = await response.json()
        
        setExchange(data.exchange)
        setTradingMode(data.trading_mode)
        setSlippage(data.slippage.toString())
        setStopLoss(data.stop_loss_percent.toString())
        setTakeProfit(data.take_profit_percent.toString())
        setPositionSize(data.default_position_size.toString())
        
        // Phase 2 settings
        setPaperTradingEnabled(data.paper_trading_enabled || false)
        setTrailingStopEnabled(data.trailing_stop_enabled || false)
        setTrailingStopPercent(data.trailing_stop_percent?.toString() || '1.0')
        setNotificationsEnabled(data.enable_notifications || false)
        setNotificationEmail(data.notification_email || '')
        setTieredTpEnabled(data.tiered_tp_enabled || false)
      } catch (error) {
        console.error('Failed to fetch settings:', error)
      }
    }
    
    fetchSettings()
  }, [apiUrl, token])

  const handleSaveSettings = async () => {
    setSaving(true)
    try {
      const response = await fetch(`${apiUrl}/settings`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          exchange,
          trading_mode: tradingMode,
          slippage: parseFloat(slippage),
          stop_loss_percent: parseFloat(stopLoss),
          take_profit_percent: parseFloat(takeProfit),
          default_position_size: parseFloat(positionSize),
          // Phase 2 settings
          paper_trading_enabled: paperTradingEnabled,
          trailing_stop_enabled: trailingStopEnabled,
          trailing_stop_percent: parseFloat(trailingStopPercent),
          enable_notifications: notificationsEnabled,
          notification_email: notificationEmail,
          tiered_tp_enabled: tieredTpEnabled,
        }),
      })

      const data = await response.json()

      if (data.success) {
        toast({
          title: 'Success',
          description: 'Settings saved successfully',
        })
        onStatusUpdate()
      } else {
        toast({
          title: 'Error',
          description: 'Failed to save settings',
          variant: 'destructive',
        })
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to save settings',
        variant: 'destructive',
      })
    } finally {
      setSaving(false)
    }
  }

  const runDiagnostics = async () => {
    setRunningDiagnostics(true)
    try {
      const response = await fetch(`${apiUrl}/diagnostics`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      const data = await response.json()
      setDiagnostics(data)
      
      const allPassed = data.tests.every((test: any) => test.passed)
      
      toast({
        title: allPassed ? 'All Tests Passed' : 'Some Tests Failed',
        description: `${data.tests.filter((t: any) => t.passed).length} of ${data.tests.length} tests passed`,
        variant: allPassed ? 'default' : 'destructive',
      })
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to run diagnostics',
        variant: 'destructive',
      })
    } finally {
      setRunningDiagnostics(false)
    }
  }

  return (
    <div className="space-y-6">
      <Card className="shadow-lg border-slate-200 dark:border-slate-700">
        <CardHeader>
          <CardTitle className="text-2xl">Trading Settings</CardTitle>
          <CardDescription>Configure your trading parameters and preferences</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <Label htmlFor="exchange-select">Exchange</Label>
              <select
                id="exchange-select"
                value={exchange}
                onChange={(e) => setExchange(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
              >
                <option value="binance">Binance</option>
                <option value="coinbase">Coinbase</option>
                <option value="kraken">Kraken</option>
                <option value="bybit">Bybit</option>
                <option value="okx">OKX</option>
              </select>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Select your preferred exchange
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="trading-mode">Trading Mode</Label>
              <select
                id="trading-mode"
                value={tradingMode}
                onChange={(e) => setTradingMode(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
              >
                <option value="market">Market Orders Only</option>
                <option value="limit">Limit Orders Only</option>
                <option value="market_limit_fallback">Market with Limit Fallback</option>
              </select>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Choose how orders are executed
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="slippage">Slippage (%)</Label>
              <Input
                id="slippage"
                type="number"
                step="0.1"
                min="0"
                max="10"
                value={slippage}
                onChange={(e) => setSlippage(e.target.value)}
              />
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Maximum acceptable slippage
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="stop-loss">Stop Loss (%)</Label>
              <Input
                id="stop-loss"
                type="number"
                step="0.1"
                min="0"
                max="100"
                value={stopLoss}
                onChange={(e) => setStopLoss(e.target.value)}
              />
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Automatic stop loss percentage
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="take-profit">Take Profit (%)</Label>
              <Input
                id="take-profit"
                type="number"
                step="0.1"
                min="0"
                max="100"
                value={takeProfit}
                onChange={(e) => setTakeProfit(e.target.value)}
              />
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Automatic take profit percentage
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="position-size">Default Position Size (USDT)</Label>
              <Input
                id="position-size"
                type="number"
                step="10"
                min="10"
                value={positionSize}
                onChange={(e) => setPositionSize(e.target.value)}
              />
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Default position size in USDT
              </p>
            </div>
          </div>

          <div className="flex justify-end pt-4 border-t border-slate-200 dark:border-slate-700">
            <Button
              onClick={handleSaveSettings}
              disabled={saving}
              className="px-8"
            >
              {saving ? 'Saving...' : 'Save Settings'}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="shadow-lg border-slate-200 dark:border-slate-700">
        <CardHeader>
          <CardTitle className="text-2xl">Advanced Features (Phase 2)</CardTitle>
          <CardDescription>Enable advanced trading features and notifications</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
              <div className="space-y-1">
                <Label htmlFor="paper-trading" className="text-base font-semibold">Paper Trading Mode</Label>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Simulate trades without executing on exchange (no real money)
                </p>
              </div>
              <input
                id="paper-trading"
                type="checkbox"
                checked={paperTradingEnabled}
                onChange={(e) => setPaperTradingEnabled(e.target.checked)}
                className="w-5 h-5 rounded border-slate-300 dark:border-slate-600"
              />
            </div>

            <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
              <div className="space-y-1 flex-1">
                <Label htmlFor="trailing-stop" className="text-base font-semibold">Trailing Stop-Loss</Label>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Automatically adjust stop-loss as price moves favorably
                </p>
                {trailingStopEnabled && (
                  <div className="mt-2">
                    <Label htmlFor="trailing-stop-percent" className="text-sm">Trailing Stop %</Label>
                    <Input
                      id="trailing-stop-percent"
                      type="number"
                      step="0.1"
                      min="0.1"
                      max="10"
                      value={trailingStopPercent}
                      onChange={(e) => setTrailingStopPercent(e.target.value)}
                      className="w-32 mt-1"
                    />
                  </div>
                )}
              </div>
              <input
                id="trailing-stop"
                type="checkbox"
                checked={trailingStopEnabled}
                onChange={(e) => setTrailingStopEnabled(e.target.checked)}
                className="w-5 h-5 rounded border-slate-300 dark:border-slate-600"
              />
            </div>

            <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
              <div className="space-y-1 flex-1">
                <Label htmlFor="notifications" className="text-base font-semibold">Email Notifications</Label>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Receive email alerts for trades and system events
                </p>
                {notificationsEnabled && (
                  <div className="mt-2">
                    <Label htmlFor="notification-email" className="text-sm">Email Address</Label>
                    <Input
                      id="notification-email"
                      type="email"
                      placeholder="your@email.com"
                      value={notificationEmail}
                      onChange={(e) => setNotificationEmail(e.target.value)}
                      className="mt-1"
                    />
                  </div>
                )}
              </div>
              <input
                id="notifications"
                type="checkbox"
                checked={notificationsEnabled}
                onChange={(e) => setNotificationsEnabled(e.target.checked)}
                className="w-5 h-5 rounded border-slate-300 dark:border-slate-600"
              />
            </div>

            <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
              <div className="space-y-1">
                <Label htmlFor="tiered-tp" className="text-base font-semibold">Tiered Take-Profits</Label>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Close positions in stages at multiple profit levels
                </p>
              </div>
              <input
                id="tiered-tp"
                type="checkbox"
                checked={tieredTpEnabled}
                onChange={(e) => setTieredTpEnabled(e.target.checked)}
                className="w-5 h-5 rounded border-slate-300 dark:border-slate-600"
              />
            </div>
          </div>

          <div className="flex justify-end pt-4 border-t border-slate-200 dark:border-slate-700">
            <Button
              onClick={handleSaveSettings}
              disabled={saving}
              className="px-8"
            >
              {saving ? 'Saving...' : 'Save All Settings'}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="shadow-lg border-slate-200 dark:border-slate-700">
        <CardHeader>
          <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
            <div>
              <CardTitle className="text-2xl">System Diagnostics</CardTitle>
              <CardDescription>Check system health and connectivity</CardDescription>
            </div>
            <Button
              onClick={runDiagnostics}
              disabled={runningDiagnostics}
              variant="outline"
            >
              {runningDiagnostics ? 'Running...' : 'Run Diagnostics'}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {diagnostics ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div className="p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
                  <p className="text-sm text-slate-600 dark:text-slate-400">Exchange</p>
                  <p className="text-lg font-semibold capitalize">{diagnostics.exchange}</p>
                </div>
                <div className="p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
                  <p className="text-sm text-slate-600 dark:text-slate-400">Timestamp</p>
                  <p className="text-lg font-semibold">
                    {new Date(diagnostics.timestamp).toLocaleString()}
                  </p>
                </div>
              </div>

              <div className="space-y-3">
                {diagnostics.tests.map((test: any, index: number) => (
                  <Alert
                    key={index}
                    className={
                      test.passed
                        ? 'border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20'
                        : 'border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20'
                    }
                  >
                    <div className="flex items-start space-x-3">
                      {test.passed ? (
                        <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400 mt-0.5" />
                      ) : (
                        <XCircle className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5" />
                      )}
                      <div className="flex-1">
                        <p className="font-semibold text-slate-900 dark:text-slate-100">
                          {test.name}
                        </p>
                        <AlertDescription className="text-sm mt-1">
                          {test.message}
                        </AlertDescription>
                      </div>
                      <Badge variant={test.passed ? 'default' : 'destructive'}>
                        {test.passed ? 'PASS' : 'FAIL'}
                      </Badge>
                    </div>
                  </Alert>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-center py-12">
              <AlertTriangle className="w-12 h-12 text-slate-400 mx-auto mb-4" />
              <p className="text-slate-600 dark:text-slate-400">
                Click "Run Diagnostics" to check system health
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="shadow-lg border-slate-200 dark:border-slate-700">
        <CardHeader>
          <CardTitle className="text-2xl">Current Configuration</CardTitle>
          <CardDescription>Overview of your current settings</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
              <p className="text-sm text-slate-600 dark:text-slate-400 mb-1">Exchange</p>
              <p className="text-lg font-semibold capitalize">{systemStatus?.exchange || 'Not set'}</p>
            </div>
            <div className="p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
              <p className="text-sm text-slate-600 dark:text-slate-400 mb-1">Trading Mode</p>
              <p className="text-lg font-semibold capitalize">
                {systemStatus?.settings.trading_mode.replace('_', ' ') || 'Not set'}
              </p>
            </div>
            <div className="p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
              <p className="text-sm text-slate-600 dark:text-slate-400 mb-1">Slippage</p>
              <p className="text-lg font-semibold">{systemStatus?.settings.slippage || 0}%</p>
            </div>
            <div className="p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
              <p className="text-sm text-slate-600 dark:text-slate-400 mb-1">Stop Loss</p>
              <p className="text-lg font-semibold">{systemStatus?.settings.stop_loss_percent || 0}%</p>
            </div>
            <div className="p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
              <p className="text-sm text-slate-600 dark:text-slate-400 mb-1">Take Profit</p>
              <p className="text-lg font-semibold">{systemStatus?.settings.take_profit_percent || 0}%</p>
            </div>
            <div className="p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
              <p className="text-sm text-slate-600 dark:text-slate-400 mb-1">Position Size</p>
              <p className="text-lg font-semibold">${systemStatus?.settings.default_position_size || 0}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
