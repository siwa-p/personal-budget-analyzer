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
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts'

type BudgetWithCategory = {
  id: number
  user_id: number
  year: number
  month: number
  category_id: number | null
  amount: number
  spent: number
  remaining: number
  percentage_used: number
  category_name: string
  created_at: string
  updated_at: string
}

type BudgetDataPoint = {
  name: string
  budget: number
  actual: number
}

type SelectedMonth = {
  year: number
  month: number
}

type MonthOption = {
  year: number
  month: number
  label: string
  value: string
}

type BudgetVsActualProps = {
  token: string
}

const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function getLastNMonths(n: number): MonthOption[] {
  const now = new Date()
  return Array.from({ length: n }, (_, i) => {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    const year = d.getFullYear()
    const month = d.getMonth() + 1
    return {
      year,
      month,
      label: d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' }),
      value: `${year}-${month}`
    }
  })
}

function buildBarData(budgets: BudgetWithCategory[]): BudgetDataPoint[] {
  return budgets.map(b => ({
    name: b.category_name,
    budget: b.amount,
    actual: b.spent
  }))
}

const MONTH_OPTIONS = getLastNMonths(12)

function BudgetVsActual({ token }: BudgetVsActualProps) {
  const muiTheme = useTheme()
  const isDark = muiTheme.palette.mode === 'dark'

  const now = new Date()
  const [selectedMonth, setSelectedMonth] = useState<SelectedMonth>({
    year: now.getFullYear(),
    month: now.getMonth() + 1
  })
  const [chartData, setChartData] = useState<BudgetDataPoint[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return

    const fetchData = async () => {
      setIsLoading(true)
      setError(null)

      try {
        const response = await fetch(
          `${apiUrl}/api/v1/budgets/month?year=${selectedMonth.year}&month=${selectedMonth.month}`,
          { headers: { Authorization: `Bearer ${token}` } }
        )

        if (!response.ok) throw new Error('Failed to load budget data.')

        const budgets = (await response.json()) as BudgetWithCategory[]
        setChartData(buildBarData(budgets))
      } catch (fetchError) {
        setError(
          fetchError instanceof Error ? fetchError.message : 'Unknown error loading budget data.'
        )
      } finally {
        setIsLoading(false)
      }
    }

    fetchData()
  }, [token, selectedMonth])

  const tooltipBg = muiTheme.palette.background.paper
  const tooltipBorder = muiTheme.palette.divider
  const axisColor = muiTheme.palette.text.secondary
  const gridColor = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)'

  const selectedValue = `${selectedMonth.year}-${selectedMonth.month}`
  const selectedLabel =
    MONTH_OPTIONS.find(o => o.value === selectedValue)?.label ?? selectedValue

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
          Budget vs. Actual
        </Typography>
        <FormControl size="small" sx={{ minWidth: 180 }}>
          <InputLabel id="budget-month-label">Month</InputLabel>
          <Select
            labelId="budget-month-label"
            label="Month"
            value={selectedValue}
            onChange={(e: { target: { value: string } }) => {
              const [year, month] = e.target.value.split('-').map(Number)
              setSelectedMonth({ year, month })
            }}
          >
            {MONTH_OPTIONS.map(opt => (
              <MenuItem key={opt.value} value={opt.value}>
                {opt.label}
              </MenuItem>
            ))}
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
      ) : chartData.length === 0 ? (
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            height: 240
          }}
        >
          <Typography color="text.secondary">
            No budgets set for {selectedLabel}.
          </Typography>
        </Box>
      ) : (
        <ResponsiveContainer width="100%" height={360}>
          <BarChart
            data={chartData}
            margin={{ left: 8, right: 24, top: 8, bottom: 56 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
            <XAxis
              dataKey="name"
              angle={-35}
              textAnchor="end"
              tick={{ fill: axisColor, fontSize: 11 }}
              axisLine={{ stroke: gridColor }}
              tickLine={false}
              interval={0}
              height={60}
            />
            <YAxis
              tick={{ fill: axisColor, fontSize: 12 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v: number) =>
                v >= 1000 ? `$${(v / 1000).toFixed(1)}k` : `$${v}`
              }
            />
            <Tooltip
              formatter={(value: number, name: string) => [
                `$${value.toFixed(2)}`,
                name === 'budget' ? 'Budget' : 'Actual'
              ]}
              contentStyle={{
                backgroundColor: tooltipBg,
                border: `1px solid ${tooltipBorder}`,
                borderRadius: 8
              }}
              labelStyle={{ color: muiTheme.palette.text.primary, fontWeight: 600 }}
            />
            <Legend
              content={() => (
                <Box sx={{ display: 'flex', gap: 3, justifyContent: 'center', mt: 1, flexWrap: 'wrap' }}>
                  {[
                    { color: '#4e9af1', label: 'Budget' },
                    { color: '#2ecc71', label: 'Actual (under)' },
                    { color: '#e74c3c', label: 'Actual (over)' }
                  ].map(({ color, label }) => (
                    <Box key={label} sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                      <Box sx={{ width: 12, height: 12, borderRadius: 0.5, backgroundColor: color, flexShrink: 0 }} />
                      <Typography variant="caption" sx={{ color: axisColor }}>{label}</Typography>
                    </Box>
                  ))}
                </Box>
              )}
            />
            <Bar dataKey="budget" name="budget" fill="#4e9af1" radius={[4, 4, 0, 0]} />
            <Bar dataKey="actual" name="actual" radius={[4, 4, 0, 0]}>
              {chartData.map((entry: BudgetDataPoint, index: number) => (
                <Cell
                  key={index}
                  fill={entry.actual > entry.budget ? '#e74c3c' : '#2ecc71'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </Paper>
  )
}

export default BudgetVsActual
