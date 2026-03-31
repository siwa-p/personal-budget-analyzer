import { Component, ReactNode, Suspense, use, useMemo, useState } from 'react'
import {
  Alert,
  Box,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  SelectChangeEvent,
  Typography
} from '@mui/material'
import { useTheme } from '@mui/material/styles'
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

type CategoryPoint = {
  category: string
  total: number
}

type CategoryDistributionResponse = {
  start_date: string
  end_date: string
  category_distribution: CategoryPoint[]
}

type PieDataPoint = {
  name: string
  value: number
}

type MonthRange = 'last' | 3 | 6 | 12

type SpendingPieChartProps = {
  token: string
}

const COLORS = [
  '#4e9af1', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6',
  '#1abc9c', '#e67e22', '#e91e63', '#95a5a6'
]

const TOP_N = 8

const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function getDateRange(monthRange: MonthRange) {
  const now = new Date()

  if (monthRange === 'last') {
    const first = new Date(now.getFullYear(), now.getMonth() - 1, 1)
    const last = new Date(now.getFullYear(), now.getMonth(), 0)
    const fmt = (d: Date) =>
      `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    return { startDateStr: fmt(first), endDateStr: fmt(last) }
  }

  const endYear = now.getFullYear()
  const endMonth = now.getMonth() + 1
  const startDate = new Date(now.getFullYear(), now.getMonth() - (monthRange - 1), 1)
  const lastDay = new Date(endYear, endMonth, 0).getDate()

  return {
    startDateStr: `${startDate.getFullYear()}-${String(startDate.getMonth() + 1).padStart(2, '0')}-01`,
    endDateStr: `${endYear}-${String(endMonth).padStart(2, '0')}-${lastDay}`
  }
}

function buildPieData(points: CategoryPoint[]): PieDataPoint[] {
  const top = points.slice(0, TOP_N)
  const rest = points.slice(TOP_N)
  const data = top.map(p => ({ name: p.category, value: p.total }))
  if (rest.length > 0) {
    const otherTotal = rest.reduce((sum, p) => sum + p.total, 0)
    data.push({ name: 'Other', value: otherTotal })
  }
  return data
}

// Pure async function — fetched outside of React, no hooks.
// React 19: this promise is passed to use() in the inner component.
async function fetchPieData(token: string, monthRange: MonthRange): Promise<PieDataPoint[]> {
  const { startDateStr, endDateStr } = getDateRange(monthRange)
  const response = await fetch(
    `${apiUrl}/api/v1/analytics/category-distribution` +
      `?start_date=${startDateStr}&end_date=${endDateStr}`,
    { headers: { Authorization: `Bearer ${token}` } }
  )
  if (!response.ok) throw new Error('Failed to load category distribution data.')
  const data = (await response.json()) as CategoryDistributionResponse
  return buildPieData(data.category_distribution)
}

// Minimal class ErrorBoundary — still the React-recommended pattern for catching
// errors thrown by use(). Renders an Alert when the promise rejects.
class ChartErrorBoundary extends Component<{ children: ReactNode }, { error: string | null }> {
  state: { error: string | null } = { error: null }

  constructor(props: { children: ReactNode }) {
    super(props)
  }

  static getDerivedStateFromError(err: Error) {
    return { error: err.message }
  }

  render() {
    if (this.state.error) {
      return <Alert severity="error" sx={{ mt: 1 }}>{this.state.error}</Alert>
    }
    return this.props.children
  }
}

// Inner component: use() suspends the render until dataPromise resolves.
// No loading/error state needed — Suspense handles loading, ErrorBoundary handles errors.
function PieChartContent({ dataPromise }: { dataPromise: Promise<PieDataPoint[]> }) {
  const chartData = use(dataPromise)
  const muiTheme = useTheme()
  const tooltipBg = muiTheme.palette.background.paper
  const tooltipBorder = muiTheme.palette.divider

  if (chartData.length === 0) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 320 }}>
        <Typography color="text.secondary">No spending data for this period.</Typography>
      </Box>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={320}>
      <PieChart>
        <Pie
          data={chartData}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          outerRadius={110}
          innerRadius={55}
        >
          {chartData.map((_: PieDataPoint, index: number) => (
            <Cell key={index} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value: number, name: string) => [`$${value.toFixed(2)}`, name]}
          contentStyle={{
            backgroundColor: tooltipBg,
            border: `1px solid ${tooltipBorder}`,
            borderRadius: 8
          }}
          labelStyle={{ color: muiTheme.palette.text.primary }}
        />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  )
}

// Outer component: owns the range selector and the Suspense/ErrorBoundary boundary.
// useMemo ensures a new promise is only created when token or monthRange changes —
// without it, every render would create a new promise and cause an infinite suspense loop.
function SpendingPieChart({ token }: SpendingPieChartProps) {
  const [monthRange, setMonthRange] = useState<MonthRange>(6)

  const dataPromise = useMemo(
    () => fetchPieData(token, monthRange),
    [token, monthRange]
  )

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
          Spending by Category
        </Typography>
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel id="pie-range-label">Time Range</InputLabel>
          <Select
            labelId="pie-range-label"
            label="Time Range"
            value={monthRange}
            onChange={(e: SelectChangeEvent<MonthRange>) => setMonthRange(e.target.value as MonthRange)}
          >
            <MenuItem value="last">Last month</MenuItem>
            <MenuItem value={3}>Last 3 months</MenuItem>
            <MenuItem value={6}>Last 6 months</MenuItem>
            <MenuItem value={12}>Last 12 months</MenuItem>
          </Select>
        </FormControl>
      </Box>

      <ChartErrorBoundary>
        <Suspense
          fallback={
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
              <CircularProgress />
            </Box>
          }
        >
          <PieChartContent dataPromise={dataPromise} />
        </Suspense>
      </ChartErrorBoundary>
    </Paper>
  )
}

export default SpendingPieChart
