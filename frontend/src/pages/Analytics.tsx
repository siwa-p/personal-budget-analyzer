import { useState } from 'react'
import { Link as RouterLink } from 'react-router-dom'
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Container,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Typography
} from '@mui/material'
import TrendLineGraph from '../components/charts/TrendLineGraph'
import SpendingPieChart from '../components/charts/SpendingPieChart'
import BudgetVsActual from '../components/charts/BudgetVsActual'

function Analytics() {
  const [token] = useState(() => localStorage.getItem('access_token') || '')
  const [pdfLoading, setPdfLoading] = useState(false)
  const [pdfError, setPdfError] = useState<string | null>(null)

  const [monthlyRange, setMonthlyRange] = useState<3 | 6 | 12>(6)
  const currentYear = new Date().getFullYear()
  const [year, setYear] = useState<number>(currentYear)

  const getLastNMonthsRange = (n: 3 | 6 | 12) => {
    const now = new Date()
    const endYear = now.getFullYear()
    const endMonth = now.getMonth() + 1
    const startDate = new Date(now.getFullYear(), now.getMonth() - (n - 1), 1)
    const startYear = startDate.getFullYear()
    const startMonth = startDate.getMonth() + 1
    return { startYear, startMonth, endYear, endMonth }
  }

  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  const downloadPdf = async (url: string, filename: string) => {
    setPdfLoading(true)
    setPdfError(null)
    try {
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (!res.ok) throw new Error('Failed to generate PDF report.')
      const blob = await res.blob()
      const objectUrl = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = objectUrl
      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(objectUrl)
    } catch (err) {
      setPdfError(err instanceof Error ? err.message : 'Unknown error generating PDF.')
    } finally {
      setPdfLoading(false)
    }
  }

  return (
    <Container maxWidth="lg" sx={{ py: 6 }}>
      <Typography variant="h4" sx={{ fontWeight: 600, mb: 4 }}>
        Analytics
      </Typography>

      {!token && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          You must be logged in to view analytics.
          <Button component={RouterLink} to="/login" size="small" sx={{ ml: 2 }} variant="outlined">
            Go to login
          </Button>
        </Alert>
      )}

      {token && (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 4 }}>
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <TrendLineGraph token={token} />
            </Box>
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <SpendingPieChart token={token} />
            </Box>
          </Box>
          <BudgetVsActual token={token} />

          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
              PDF Reports (Spending)
            </Typography>

            {pdfError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {pdfError}
              </Alert>
            )}

            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center' }}>
              <FormControl size="small" sx={{ minWidth: 220 }}>
                <InputLabel id="monthly-range-label">Monthly range</InputLabel>
                <Select
                  labelId="monthly-range-label"
                  label="Monthly range"
                  value={monthlyRange}
                  onChange={(e) => setMonthlyRange(e.target.value as 3 | 6 | 12)}
                  disabled={pdfLoading}
                >
                  <MenuItem value={3}>Last 3 months</MenuItem>
                  <MenuItem value={6}>Last 6 months</MenuItem>
                  <MenuItem value={12}>Last 12 months</MenuItem>
                </Select>
              </FormControl>

              <Button
                variant="outlined"
                onClick={() => {
                  const { startYear, startMonth, endYear, endMonth } = getLastNMonthsRange(monthlyRange)
                  const url = `${apiUrl}/api/v1/analytics/spending-report/pdf?report_type=monthly&start_year=${startYear}&start_month=${startMonth}&end_year=${endYear}&end_month=${endMonth}`
                  const filename = `spending-report-monthly-${startYear}-${String(startMonth).padStart(2, '0')}-to-${endYear}-${String(endMonth).padStart(2, '0')}.pdf`
                  void downloadPdf(url, filename)
                }}
                disabled={!token || pdfLoading}
                sx={{ height: 40 }}
              >
                {pdfLoading ? <CircularProgress size={18} /> : 'Download Monthly PDF'}
              </Button>

              <FormControl size="small" sx={{ minWidth: 180 }}>
                <InputLabel id="year-label">Year</InputLabel>
                <Select
                  labelId="year-label"
                  label="Year"
                  value={year}
                  onChange={(e) => setYear(Number(e.target.value))}
                  disabled={pdfLoading}
                >
                  {Array.from({ length: 6 }, (_, i) => currentYear - i).map((y) => (
                    <MenuItem key={y} value={y}>
                      {y}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Button
                variant="contained"
                onClick={() => {
                  const url = `${apiUrl}/api/v1/analytics/spending-report/pdf?report_type=yearly&year=${year}`
                  const filename = `spending-report-yearly-${year}.pdf`
                  void downloadPdf(url, filename)
                }}
                disabled={!token || pdfLoading}
                sx={{ height: 40 }}
              >
                {pdfLoading ? <CircularProgress size={18} /> : 'Download Yearly PDF'}
              </Button>
            </Box>
          </Paper>
        </Box>
      )}
    </Container>
  )
}

export default Analytics
