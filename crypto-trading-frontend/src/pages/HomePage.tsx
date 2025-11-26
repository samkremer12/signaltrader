import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Copy, CheckCircle2, XCircle, Activity, TrendingUp, TrendingDown } from 'lucide-react'
import { SystemStatus } from '../App'

interface HomePageProps {
  systemStatus: SystemStatus | null
  onStatusUpdate: () => void
  apiUrl: string
  toast: any
  token: string
}

export default function HomePage({ systemStatus, onStatusUpdate, apiUrl, toast, token }: HomePageProps) {
  const [apiKey, setApiKey] = useState('')
  const [apiSecret, setApiSecret] = useState('')
  const [exchange, setExchange] = useState('binance')
  const [saving, setSaving] = useState(false)
  const [webhookUrl, setWebhookUrl] = useState('')

  useEffect(() => {
    if (systemStatus?.webhook_url) {
      const fullUrl = `${apiUrl}${systemStatus.webhook_url}`
      setWebhookUrl(fullUrl)
    }
  }, [apiUrl, systemStatus])

  const handleSaveApiKeys = async () => {
    if (!apiKey || !apiSecret) {
      toast({
        title: 'Error',
        description: 'Please enter both API key and secret',
        variant: 'destructive',
      })
      return
    }

    setSaving(true)
    try {
      const response = await fetch(`${apiUrl}/set-api-key`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ api_key: apiKey, api_secret: apiSecret, exchange }),
      })

      const data = await response.json()

      if (data.success) {
        toast({
          title: 'Success',
          description: data.message,
        })
        onStatusUpdate()
        setApiKey('')
        setApiSecret('')
      } else {
        toast({
          title: 'Warning',
          description: data.message,
          variant: 'destructive',
        })
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to save API keys',
        variant: 'destructive',
      })
    } finally {
      setSaving(false)
    }
  }

  const handleToggleAutoTrading = async (enabled: boolean) => {
    try {
      const response = await fetch(`${apiUrl}/settings`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ auto_trading_enabled: enabled }),
      })

      const data = await response.json()

      if (data.success) {
        toast({
          title: enabled ? 'Auto-Trading Enabled' : 'Auto-Trading Disabled',
          description: `Auto-trading has been ${enabled ? 'enabled' : 'disabled'}`,
        })
        onStatusUpdate()
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to toggle auto-trading',
        variant: 'destructive',
      })
    }
  }

  const copyWebhookUrl = () => {
    navigator.clipboard.writeText(webhookUrl)
    toast({
      title: 'Copied',
      description: 'Webhook URL copied to clipboard',
    })
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="shadow-lg border-slate-200 dark:border-slate-700">
          <CardHeader>
            <CardTitle className="text-xl">API Configuration</CardTitle>
            <CardDescription>Configure your exchange API credentials</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="exchange">Exchange</Label>
              <select
                id="exchange"
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
            </div>

            <div className="space-y-2">
              <Label htmlFor="apiKey">API Key</Label>
              <Input
                id="apiKey"
                type="text"
                placeholder="Enter your API key"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="apiSecret">API Secret</Label>
              <Input
                id="apiSecret"
                type="password"
                placeholder="Enter your API secret"
                value={apiSecret}
                onChange={(e) => setApiSecret(e.target.value)}
              />
            </div>

            <Button
              onClick={handleSaveApiKeys}
              disabled={saving}
              className="w-full"
            >
              {saving ? 'Saving...' : 'Save Settings'}
            </Button>

            <div className="flex items-center justify-between pt-4 border-t border-slate-200 dark:border-slate-700">
              <div className="space-y-1">
                <Label htmlFor="auto-trading">Auto-Trading</Label>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Enable automated trading from webhooks
                </p>
              </div>
              <Switch
                id="auto-trading"
                checked={systemStatus?.auto_trading_enabled || false}
                onCheckedChange={handleToggleAutoTrading}
              />
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-lg border-slate-200 dark:border-slate-700">
          <CardHeader>
            <CardTitle className="text-xl">Webhook Configuration</CardTitle>
            <CardDescription>Use this URL in TradingView alerts</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Webhook URL</Label>
              <div className="flex space-x-2">
                <Input
                  value={webhookUrl}
                  readOnly
                  className="font-mono text-sm"
                />
                <Button
                  variant="outline"
                  size="icon"
                  onClick={copyWebhookUrl}
                >
                  <Copy className="w-4 h-4" />
                </Button>
              </div>
            </div>

            <Alert>
              <AlertDescription className="text-sm">
                <strong>TradingView Setup:</strong>
                <ol className="list-decimal list-inside mt-2 space-y-1">
                  <li>Create an alert in TradingView</li>
                  <li>Set Webhook URL to the URL above</li>
                  <li>Use this JSON format in the message:</li>
                </ol>
                <pre className="mt-2 p-2 bg-slate-100 dark:bg-slate-800 rounded text-xs overflow-x-auto">
{`{
  "action": "buy",
  "symbol": "BTCUSDT",
  "price": "{{close}}"
}`}
                </pre>
              </AlertDescription>
            </Alert>

            <div className="flex items-center space-x-2 pt-2">
              {systemStatus?.connected ? (
                <>
                  <CheckCircle2 className="w-5 h-5 text-green-500" />
                  <span className="text-sm font-medium text-green-600 dark:text-green-400">
                    Connected to {systemStatus.exchange}
                  </span>
                </>
              ) : (
                <>
                  <XCircle className="w-5 h-5 text-red-500" />
                  <span className="text-sm font-medium text-red-600 dark:text-red-400">
                    Not Connected
                  </span>
                </>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="shadow-lg border-slate-200 dark:border-slate-700">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-slate-600 dark:text-slate-400">
              Current PnL
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center space-x-2">
              {(systemStatus?.current_pnl || 0) >= 0 ? (
                <TrendingUp className="w-5 h-5 text-green-500" />
              ) : (
                <TrendingDown className="w-5 h-5 text-red-500" />
              )}
              <span className={`text-2xl font-bold ${
                (systemStatus?.current_pnl || 0) >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
              }`}>
                ${(systemStatus?.current_pnl || 0).toFixed(2)}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-lg border-slate-200 dark:border-slate-700">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-slate-600 dark:text-slate-400">
              Total PnL
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center space-x-2">
              {(systemStatus?.total_pnl || 0) >= 0 ? (
                <TrendingUp className="w-5 h-5 text-green-500" />
              ) : (
                <TrendingDown className="w-5 h-5 text-red-500" />
              )}
              <span className={`text-2xl font-bold ${
                (systemStatus?.total_pnl || 0) >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
              }`}>
                ${(systemStatus?.total_pnl || 0).toFixed(2)}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-lg border-slate-200 dark:border-slate-700">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-slate-600 dark:text-slate-400">
              Total Trades
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center space-x-2">
              <Activity className="w-5 h-5 text-blue-500" />
              <span className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                {systemStatus?.total_trades || 0}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-lg border-slate-200 dark:border-slate-700">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-slate-600 dark:text-slate-400">
              Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Badge
              variant={systemStatus?.auto_trading_enabled ? 'default' : 'secondary'}
              className="text-sm"
            >
              {systemStatus?.auto_trading_enabled ? 'Active' : 'Inactive'}
            </Badge>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="shadow-lg border-slate-200 dark:border-slate-700">
          <CardHeader>
            <CardTitle className="text-xl">Current Position</CardTitle>
          </CardHeader>
          <CardContent>
            {systemStatus?.current_position ? (
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-slate-600 dark:text-slate-400">Symbol</span>
                  <span className="font-semibold">{systemStatus.current_position.symbol}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-slate-600 dark:text-slate-400">Side</span>
                  <Badge variant={systemStatus.current_position.side === 'LONG' ? 'default' : 'destructive'}>
                    {systemStatus.current_position.side}
                  </Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-slate-600 dark:text-slate-400">Entry Price</span>
                  <span className="font-semibold">${systemStatus.current_position.entry_price.toFixed(2)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-slate-600 dark:text-slate-400">Size</span>
                  <span className="font-semibold">{systemStatus.current_position.size.toFixed(4)}</span>
                </div>
              </div>
            ) : (
              <p className="text-slate-500 dark:text-slate-400 text-center py-8">No open position</p>
            )}
          </CardContent>
        </Card>

        <Card className="shadow-lg border-slate-200 dark:border-slate-700">
          <CardHeader>
            <CardTitle className="text-xl">Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {systemStatus?.last_webhook && (
                <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="text-sm font-medium text-blue-900 dark:text-blue-100">
                        Last Webhook
                      </p>
                      <p className="text-xs text-blue-700 dark:text-blue-300 mt-1">
                        {systemStatus.last_webhook.action.toUpperCase()} {systemStatus.last_webhook.symbol}
                      </p>
                    </div>
                    <span className="text-xs text-blue-600 dark:text-blue-400">
                      {new Date(systemStatus.last_webhook.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              )}

              {systemStatus?.last_order && (
                <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="text-sm font-medium text-green-900 dark:text-green-100">
                        Last Order
                      </p>
                      <p className="text-xs text-green-700 dark:text-green-300 mt-1">
                        {systemStatus.last_order.action} {systemStatus.last_order.symbol} @ ${systemStatus.last_order.price.toFixed(2)}
                      </p>
                    </div>
                    <span className="text-xs text-green-600 dark:text-green-400">
                      {new Date(systemStatus.last_order.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              )}

              {!systemStatus?.last_webhook && !systemStatus?.last_order && (
                <p className="text-slate-500 dark:text-slate-400 text-center py-8">No recent activity</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
