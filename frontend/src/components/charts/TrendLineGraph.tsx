import { useEffect, useState } from 'react'
import {
  Alert,
  Box,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Typography
} from '@mui/material'
import { useTheme } from '@mui/material/styles'
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts'

type MonthlySpendingPoint = {
  year: number
  month: number
  total: number
}

type MonthlySpendingResponse = {
  start_date: string
  end_date: string
  monthly_spending_trend: MonthlySpendingPoint[]
}

type Transaction = {
  id: number
  amount: number
  transaction_date: string
  description: string | null
  category_id: number
  transaction_type: 'income' | 'expense'
  user_id: number
}

type ChartDataPoint = {
  label: string
  income: number
  expenses: number
}

type MonthRange = 3 | 6 | 12

type TrendLineGraphProps = {
  token: string
}

const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function getDateRange(monthRange: MonthRange) {
  const now = new Date()
  const endYear = now.getFullYear()
  const endMonth = now.getMonth() + 1

  const startDate = new Date(now.getFullYear(), now.getMonth() - (monthRange - 1), 1)
  const startYear = startDate.getFullYear()
  const startMonth = startDate.getMonth() + 1

  const lastDay = new Date(endYear, endMonth, 0).getDate()

  return {
    startYear,
    startMonth,
    endYear,
    endMonth,
    startDateStr: `${startYear}-${String(startMonth).padStart(2, '0')}-01`,
    endDateStr: `${endYear}-${String(endMonth).padStart(2, '0')}-${lastDay}`
  }
}

function aggregateIncomeByMonth(transactions: Transaction[]): Map<string, number> {
  const map = new Map<string, number>()
  for (const txn of transactions) {
    if (txn.transaction_type !== 'income') continue
    const yearMonth = txn.transaction_date.slice(0, 7)
    map.set(yearMonth, (map.get(yearMonth) ?? 0) + txn.amount)
  }
  return map
}

function buildChartData(
  monthRange: MonthRange,
  expensePoints: MonthlySpendingPoint[],
  incomeByMonth: Map<string, number>
): ChartDataPoint[] {
  const now = new Date()
  const results: ChartDataPoint[] = []

  for (let i = monthRange - 1; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    const year = d.getFullYear()
    const month = d.getMonth() + 1
    const yearMonth = `${year}-${String(month).padStart(2, '0')}`
    const label = d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })

    const expensePoint = expensePoints.find(p => p.year === year && p.month === month)
    const expenses = expensePoint?.total ?? 0
    const income = incomeByMonth.get(yearMonth) ?? 0

    results.push({ label, income, expenses })
  }

  return results
}

function TrendLineGraph({ token }: TrendLineGraphProps) {
  const muiTheme = useTheme()
  const [monthRange, setMonthRange] = useState<MonthRange>(6)
  const [chartData, setChartData] = useState<ChartDataPoint[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return

    const fetchData = async () => {
      setIsLoading(true)
      setError(null)

      try {
        const { startYear, startMonth, endYear, endMonth, startDateStr, endDateStr } =
          getDateRange(monthRange)

        const [spendingResponse, transactionsResponse] = await Promise.all([
          fetch(
            `${apiUrl}/api/v1/analytics/monthly-spending-trend` +
              `?start_year=${startYear}&start_month=${startMonth}` +
              `&end_year=${endYear}&end_month=${endMonth}`,
            { headers: { Authorization: `Bearer ${token}` } }
          ),
          fetch(
            `${apiUrl}/api/v1/transactions/?start_date=${startDateStr}&end_date=${endDateStr}&limit=1000`,
            { headers: { Authorization: `Bearer ${token}` } }
          )
        ])

        if (!spendingResponse.ok) throw new Error('Failed to load spending trend data.')
        if (!transactionsResponse.ok) throw new Error('Failed to load transaction data.')

        const spendingData = (await spendingResponse.json()) as MonthlySpendingResponse
        const transactions = (await transactionsResponse.json()) as Transaction[]

        const incomeByMonth = aggregateIncomeByMonth(transactions)
        const merged = buildChartData(monthRange, spendingData.monthly_spending_trend, incomeByMonth)
        setChartData(merged)
      } catch (fetchError) {
        setError(
          fetchError instanceof Error ? fetchError.message : 'Unknown error loading chart data.'
        )
      } finally {
        setIsLoading(false)
      }
    }

    fetchData()
  }, [token, monthRange])

  const isDark = muiTheme.palette.mode === 'dark'
  const tooltipBg = muiTheme.palette.background.paper
  const tooltipBorder = muiTheme.palette.divider
  const axisColor = muiTheme.palette.text.secondary
  const gridColor = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)'

  const INCOME_COLOR = '#2ecc71'
  const EXPENSE_COLOR = '#e74c3c'

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
          Income vs. Expenses
        </Typography>
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel id="range-label">Time Range</InputLabel>
          <Select
            labelId="range-label"
            label="Time Range"
            value={monthRange}
            onChange={e => setMonthRange(e.target.value as MonthRange)}
          >
            <MenuItem value={3}>Last 3 months</MenuItem>
            <MenuItem value={6}>Last 6 months</MenuItem>
            <MenuItem value={12}>Last 12 months</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : (
        <ResponsiveContainer width="100%" height={320}>
          <AreaChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 0 }}>
            <defs>
              <linearGradient id="incomeGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={INCOME_COLOR} stopOpacity={0.25} />
                <stop offset="95%" stopColor={INCOME_COLOR} stopOpacity={0} />
              </linearGradient>
              <linearGradient id="expenseGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={EXPENSE_COLOR} stopOpacity={0.25} />
                <stop offset="95%" stopColor={EXPENSE_COLOR} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
            <XAxis
              dataKey="label"
              tick={{ fill: axisColor, fontSize: 12 }}
              axisLine={{ stroke: gridColor }}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: axisColor, fontSize: 12 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(value: number) =>
                value >= 1000 ? `$${(value / 1000).toFixed(1)}k` : `$${value}`
              }
            />
            <Tooltip
              formatter={(value: number, name: string) => [
                `$${value.toFixed(2)}`,
                name === 'income' ? 'Income' : 'Expenses'
              ]}
              contentStyle={{
                backgroundColor: tooltipBg,
                border: `1px solid ${tooltipBorder}`,
                borderRadius: 8
              }}
              labelStyle={{ color: muiTheme.palette.text.primary, fontWeight: 600 }}
            />
            <Legend formatter={(value: string) => (value === 'income' ? 'Income' : 'Expenses')} />
            <Area
              type="monotone"
              dataKey="income"
              stroke={INCOME_COLOR}
              strokeWidth={2}
              fill="url(#incomeGradient)"
              dot={false}
              activeDot={{ r: 5 }}
            />
            <Area
              type="monotone"
              dataKey="expenses"
              stroke={EXPENSE_COLOR}
              strokeWidth={2}
              fill="url(#expenseGradient)"
              dot={false}
              activeDot={{ r: 5 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </Paper>
  )
}

export default TrendLineGraph
