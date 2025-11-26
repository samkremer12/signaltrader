import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Search, RefreshCw } from 'lucide-react'

interface Trade {
  id: string
  timestamp: string
  action: string
  symbol: string
  price: number
  size: number
  exchange: string
  result: string
  order_id?: string
}

interface TradeLogsPageProps {
  apiUrl: string
  token: string
}

export default function TradeLogsPage({ apiUrl, token }: TradeLogsPageProps) {
  const [trades, setTrades] = useState<Trade[]>([])
  const [filteredTrades, setFilteredTrades] = useState<Trade[]>([])
  const [symbolFilter, setSymbolFilter] = useState('')
  const [dateFilter, setDateFilter] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchTrades()
  }, [])

  useEffect(() => {
    filterTrades()
  }, [trades, symbolFilter, dateFilter])

  const fetchTrades = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${apiUrl}/trades?limit=1000`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      const data = await response.json()
      setTrades(data.trades || [])
    } catch (error) {
      console.error('Failed to fetch trades:', error)
    } finally {
      setLoading(false)
    }
  }

  const filterTrades = () => {
    let filtered = [...trades]

    if (symbolFilter) {
      filtered = filtered.filter(trade =>
        trade.symbol.toLowerCase().includes(symbolFilter.toLowerCase())
      )
    }

    if (dateFilter) {
      filtered = filtered.filter(trade => {
        const tradeDate = new Date(trade.timestamp).toISOString().split('T')[0]
        return tradeDate === dateFilter
      })
    }

    setFilteredTrades(filtered)
  }

  const clearFilters = () => {
    setSymbolFilter('')
    setDateFilter('')
  }

  const getActionBadgeVariant = (action: string) => {
    switch (action.toUpperCase()) {
      case 'BUY':
        return 'default'
      case 'SELL':
        return 'destructive'
      default:
        return 'secondary'
    }
  }

  const getResultBadgeVariant = (result: string) => {
    if (result.includes('SUCCESS')) {
      return 'default'
    } else if (result.includes('FAILED')) {
      return 'destructive'
    }
    return 'secondary'
  }

  return (
    <div className="space-y-6">
      <Card className="shadow-lg border-slate-200 dark:border-slate-700">
        <CardHeader>
          <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
            <div>
              <CardTitle className="text-2xl">Trade Logs</CardTitle>
              <CardDescription>View and filter your trading history</CardDescription>
            </div>
            <Button
              onClick={fetchTrades}
              disabled={loading}
              variant="outline"
              className="flex items-center space-x-2"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="space-y-2">
              <Label htmlFor="symbol-filter">Filter by Symbol</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  id="symbol-filter"
                  placeholder="e.g., BTCUSDT"
                  value={symbolFilter}
                  onChange={(e) => setSymbolFilter(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="date-filter">Filter by Date</Label>
              <Input
                id="date-filter"
                type="date"
                value={dateFilter}
                onChange={(e) => setDateFilter(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label>&nbsp;</Label>
              <Button
                onClick={clearFilters}
                variant="outline"
                className="w-full"
              >
                Clear Filters
              </Button>
            </div>
          </div>

          <div className="rounded-md border border-slate-200 dark:border-slate-700">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Timestamp</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead>Symbol</TableHead>
                    <TableHead>Price</TableHead>
                    <TableHead>Size</TableHead>
                    <TableHead>Exchange</TableHead>
                    <TableHead>Result</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredTrades.length > 0 ? (
                    filteredTrades.map((trade) => (
                      <TableRow key={trade.id}>
                        <TableCell className="font-mono text-sm">
                          {new Date(trade.timestamp).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <Badge variant={getActionBadgeVariant(trade.action)}>
                            {trade.action}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-semibold">{trade.symbol}</TableCell>
                        <TableCell className="font-mono">
                          ${trade.price.toFixed(2)}
                        </TableCell>
                        <TableCell className="font-mono">
                          {trade.size.toFixed(4)}
                        </TableCell>
                        <TableCell className="capitalize">{trade.exchange}</TableCell>
                        <TableCell>
                          <Badge variant={getResultBadgeVariant(trade.result)}>
                            {trade.result.length > 30 
                              ? trade.result.substring(0, 30) + '...' 
                              : trade.result}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8 text-slate-500 dark:text-slate-400">
                        {loading ? 'Loading trades...' : 'No trades found'}
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </div>

          <div className="mt-4 text-sm text-slate-600 dark:text-slate-400">
            Showing {filteredTrades.length} of {trades.length} trades
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
