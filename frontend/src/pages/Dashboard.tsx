import { type ReactNode, useEffect, useState } from 'react'
import { Link as RouterLink } from 'react-router-dom'
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Container,
  Divider,
  Grid,
  LinearProgress,
  Paper,
  Typography,
} from '@mui/material'
import {
  AccountBalance as AccountBalanceIcon,
  BarChart as BarChartIcon,
  EventNote as EventNoteIcon,
  Flag as FlagIcon,
  Receipt as ReceiptIcon,
  TrackChanges as TrackChangesIcon,
  TrendingDown as TrendingDownIcon,
} from '@mui/icons-material'

const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

type Bill = {
  id: number
  title: string
  amount: number | null
  due_date: string
  recurrence: string
}

type Goal = {
  id: number
  name: string
  target_amount: number
  deadline: string | null
  status: string
}

type Transaction = {
  id: number
  amount: number
  transaction_date: string
  description: string | null
  transaction_type: 'income' | 'expense'
  category_id: number
}

type BudgetWithCategory = {
  id: number
  amount: number
  spent: number
  remaining: number
  percentage_used: number
  category_name: string | null
}

type DashboardData = {
  userName: string
  monthlySpent: number
  totalBudgeted: number
  totalBudgetSpent: number
  upcomingBills: Bill[]
  activeGoals: Goal[]
  recentTransactions: Transaction[]
}

function getGreeting() {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'
  return 'Good evening'
}

function formatDate(dateStr: string) {
  return new Date(dateStr + 'T00:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

const FEATURES = [
  { icon: <ReceiptIcon fontSize="large" />, title: 'Transaction Tracking', desc: 'Log income and expenses with automatic ML-powered categorization.' },
  { icon: <BarChartIcon fontSize="large" />, title: 'Spending Analytics', desc: 'Visualize where your money goes with monthly trends and category breakdowns.' },
  { icon: <EventNoteIcon fontSize="large" />, title: 'Bill Management', desc: 'Track recurring bills and get reminders before due dates.' },
  { icon: <TrackChangesIcon fontSize="large" />, title: 'Budget Control', desc: 'Set monthly budgets per category and track progress in real time.' },
  { icon: <FlagIcon fontSize="large" />, title: 'Savings Goals', desc: 'Define goals with deadlines and watch your progress grow.' },
  { icon: <AccountBalanceIcon fontSize="large" />, title: 'Financial Overview', desc: 'See your full financial picture at a glance from the dashboard.' },
]

// Landing page for unauthenticated users
function LandingPage() {
  return (
    <Box sx={{ minHeight: '100vh', background: 'linear-gradient(160deg, #0f1f14 0%, #1a3a24 50%, #22472d 100%)', color: 'white', display: 'flex', flexDirection: 'column' }}>

      {/* Hero — two column split */}
      <Box sx={{ flex: 1, display: 'flex', alignItems: 'center' }}>
        <Container maxWidth="lg">
          <Grid container spacing={6} alignItems="center" sx={{ minHeight: '100vh' }}>

            {/* Left — branding + tagline + features */}
            <Grid item xs={12} md={7}>
              <Typography variant="h1" sx={{ fontWeight: 800, letterSpacing: 1, fontFamily: '"Trebuchet MS", Arial, sans-serif', fontSize: { xs: '3rem', md: '4.5rem' } }}>
                Ledgr
              </Typography>
              <Typography sx={{ mt: 2, fontSize: '1.2rem', color: 'rgba(255,255,255,0.85)', lineHeight: 1.8, maxWidth: 480 }}>
                Take control of your finances. Track spending, set budgets,
                and reach your savings goals — all in one place.
              </Typography>
              <Grid container spacing={2} sx={{ mt: 4 }}>
                {FEATURES.map(({ icon, title, desc }) => (
                  <Grid item xs={12} sm={6} key={title}>
                    <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'flex-start' }}>
                      <Box sx={{ color: 'rgba(255,255,255,0.75)', mt: 0.3, flexShrink: 0 }}>{icon}</Box>
                      <Box>
                        <Typography sx={{ fontWeight: 600, fontSize: '0.95rem' }}>{title}</Typography>
                        <Typography sx={{ fontSize: '0.82rem', color: 'rgba(255,255,255,0.65)', lineHeight: 1.5 }}>{desc}</Typography>
                      </Box>
                    </Box>
                  </Grid>
                ))}
              </Grid>
            </Grid>

            {/* Right — call to action card */}
            <Grid item xs={12} md={5}>
              <Box sx={{ backgroundColor: 'rgba(255,255,255,0.1)', backdropFilter: 'blur(10px)', borderRadius: 4, p: { xs: 4, md: 5 }, border: '1px solid rgba(255,255,255,0.2)' }}>
                <Typography variant="h5" sx={{ fontWeight: 700, mb: 1 }}>Get started today</Typography>
                <Typography sx={{ fontSize: '0.9rem', color: 'rgba(255,255,255,0.75)', mb: 4 }}>
                  Create a free account and start tracking your finances in minutes.
                </Typography>
                <Button
                  component={RouterLink}
                  to="/register"
                  variant="contained"
                  fullWidth
                  size="large"
                  sx={{ py: 1.5, borderRadius: 2, backgroundColor: 'white', color: '#2f5f37', fontWeight: 700, fontSize: '1rem', mb: 2, '&:hover': { backgroundColor: 'rgba(255,255,255,0.9)' } }}
                >
                  Create Account
                </Button>
                <Button
                  component={RouterLink}
                  to="/login"
                  variant="outlined"
                  fullWidth
                  size="large"
                  sx={{ py: 1.5, borderRadius: 2, borderColor: 'rgba(255,255,255,0.6)', color: 'white', fontWeight: 600, fontSize: '1rem', '&:hover': { borderColor: 'white', backgroundColor: 'rgba(255,255,255,0.1)' } }}
                >
                  Sign In
                </Button>
              </Box>
            </Grid>

          </Grid>
        </Container>
      </Box>

      {/* Footer */}
      <Box sx={{ py: 2, textAlign: 'center', backgroundColor: 'rgba(0,0,0,0.2)' }}>
        <Typography sx={{ fontSize: '0.78rem', color: 'rgba(255,255,255,0.4)' }}>
          © {new Date().getFullYear()} Ledgr. All rights reserved.
        </Typography>
      </Box>

    </Box>
  )
}

function SummaryCard({
  icon,
  label,
  value,
  sub,
  linkTo,
  linkLabel,
  color,
}: {
  icon: ReactNode
  label: string
  value: string
  sub?: string
  linkTo: string
  linkLabel: string
  color?: string
}) {
  return (
    <Paper sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column', gap: 1 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, color: color || 'primary.main' }}>
        {icon}
        <Typography variant="body2" color="text.secondary">{label}</Typography>
      </Box>
      <Typography variant="h5" fontWeight={700} sx={{ color: color }}>
        {value}
      </Typography>
      {sub && <Typography variant="caption" color="text.secondary">{sub}</Typography>}
      <Box sx={{ mt: 'auto', pt: 1 }}>
        <Button component={RouterLink} to={linkTo} size="small" variant="outlined">
          {linkLabel}
        </Button>
      </Box>
    </Paper>
  )
}

function Dashboard() {
  const token = localStorage.getItem('access_token')

  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<DashboardData | null>(null)

  useEffect(() => {
    if (!token) return

    const now = new Date()
    const year = now.getFullYear()
    const month = now.getMonth() + 1
    const startDate = `${year}-${String(month).padStart(2, '0')}-01`
    const endDate = now.toISOString().slice(0, 10)

    const load = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const headers = { Authorization: `Bearer ${token}` }
        const [userRes, txRes, budgetRes, billsRes, goalsRes] = await Promise.allSettled([
          fetch(`${apiUrl}/api/v1/users/me`, { headers }),
          fetch(`${apiUrl}/api/v1/transactions/?transaction_type=expense&start_date=${startDate}&end_date=${endDate}`, { headers }),
          fetch(`${apiUrl}/api/v1/budgets/month?year=${year}&month=${month}`, { headers }),
          fetch(`${apiUrl}/api/v1/bills/upcoming/?days_ahead=7`, { headers }),
          fetch(`${apiUrl}/api/v1/goals/?status=active`, { headers }),
        ])

        const user = userRes.status === 'fulfilled' && userRes.value.ok
          ? await userRes.value.json()
          : null

        const expenseTxns: Transaction[] = txRes.status === 'fulfilled' && txRes.value.ok
          ? await txRes.value.json()
          : []

        const budgets: BudgetWithCategory[] = budgetRes.status === 'fulfilled' && budgetRes.value.ok
          ? await budgetRes.value.json()
          : []

        const upcomingBills: Bill[] = billsRes.status === 'fulfilled' && billsRes.value.ok
          ? await billsRes.value.json()
          : []

        const activeGoals: Goal[] = goalsRes.status === 'fulfilled' && goalsRes.value.ok
          ? await goalsRes.value.json()
          : []

        // Recent 5 transactions (already expense-filtered, re-fetch all types for recent list)
        const recentRes = await fetch(`${apiUrl}/api/v1/transactions/?limit=5`, { headers })
        const recentTransactions: Transaction[] = recentRes.ok ? await recentRes.json() : []

        const monthlySpent = expenseTxns.reduce((sum, t) => sum + t.amount, 0)
        const totalBudgeted = budgets.reduce((sum, b) => sum + b.amount, 0)
        const totalBudgetSpent = budgets.reduce((sum, b) => sum + b.spent, 0)

        setData({
          userName: user?.full_name || user?.username || 'there',
          monthlySpent,
          totalBudgeted,
          totalBudgetSpent,
          upcomingBills,
          activeGoals,
          recentTransactions,
        })
      } catch {
        setError('Failed to load dashboard data.')
      } finally {
        setIsLoading(false)
      }
    }

    load()
  }, [token])

  if (!token) return <LandingPage />

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="error">{error}</Alert>
      </Container>
    )
  }

  if (!data) return null

  const budgetPct = data.totalBudgeted > 0 ? (data.totalBudgetSpent / data.totalBudgeted) * 100 : 0
  const today = new Date().toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Greeting */}
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <Box>
          <Typography variant="h4" fontWeight={700}>
            {getGreeting()}, {data.userName}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {today}
          </Typography>
        </Box>
      </Box>

      {/* Summary cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <SummaryCard
            icon={<TrendingDownIcon />}
            label="Spent this month"
            value={`$${data.monthlySpent.toFixed(2)}`}
            sub="expenses only"
            linkTo="/transactions"
            linkLabel="View transactions"
            color={data.totalBudgeted > 0 && data.monthlySpent > data.totalBudgeted ? 'error.main' : undefined}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column', gap: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'primary.main' }}>
              <AccountBalanceIcon />
              <Typography variant="body2" color="text.secondary">Budget status</Typography>
            </Box>
            {data.totalBudgeted > 0 ? (
              <>
                <Typography variant="h5" fontWeight={700}>
                  ${data.totalBudgetSpent.toFixed(0)} / ${data.totalBudgeted.toFixed(0)}
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={Math.min(budgetPct, 100)}
                  color={budgetPct >= 100 ? 'error' : budgetPct >= 80 ? 'warning' : 'success'}
                  sx={{ height: 8, borderRadius: 4 }}
                />
                <Typography variant="caption" color="text.secondary">{budgetPct.toFixed(0)}% used</Typography>
              </>
            ) : (
              <Typography variant="body2" color="text.secondary">No budgets set</Typography>
            )}
            <Box sx={{ mt: 'auto', pt: 1 }}>
              <Button component={RouterLink} to="/budgets" size="small" variant="outlined">
                View budgets
              </Button>
            </Box>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <SummaryCard
            icon={<EventNoteIcon />}
            label="Upcoming bills"
            value={String(data.upcomingBills.length)}
            sub="due in the next 7 days"
            linkTo="/bills"
            linkLabel="View bills"
            color={data.upcomingBills.length > 0 ? 'warning.main' : undefined}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <SummaryCard
            icon={<FlagIcon />}
            label="Active goals"
            value={String(data.activeGoals.length)}
            sub={data.activeGoals.length === 1 ? 'goal in progress' : 'goals in progress'}
            linkTo="/goals"
            linkLabel="View goals"
          />
        </Grid>
      </Grid>

      {/* Detail sections */}
      <Grid container spacing={3}>
        {/* Upcoming bills */}
        <Grid item xs={12} md={6}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
                Upcoming Bills
              </Typography>
              {data.upcomingBills.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  No bills due in the next 7 days.
                </Typography>
              ) : (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  {data.upcomingBills.map((bill) => (
                    <Box key={bill.id} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Box>
                        <Typography variant="body2" fontWeight={500}>{bill.title}</Typography>
                        {bill.recurrence !== 'none' && (
                          <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'capitalize' }}>
                            {bill.recurrence}
                          </Typography>
                        )}
                      </Box>
                      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                        {bill.amount != null && (
                          <Typography variant="body2" fontWeight={500}>${bill.amount.toFixed(2)}</Typography>
                        )}
                        <Chip label={`Due ${formatDate(bill.due_date)}`} size="small" color="warning" variant="outlined" />
                      </Box>
                    </Box>
                  ))}
                </Box>
              )}
              <Divider sx={{ my: 2 }} />
              <Button component={RouterLink} to="/bills" size="small">
                View all bills →
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Recent transactions */}
        <Grid item xs={12} md={6}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
                Recent Transactions
              </Typography>
              {data.recentTransactions.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  No transactions yet.
                </Typography>
              ) : (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  {data.recentTransactions.map((txn) => (
                    <Box key={txn.id} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Box>
                        <Typography variant="body2" fontWeight={500}>
                          {txn.description || '—'}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {formatDate(txn.transaction_date)}
                        </Typography>
                      </Box>
                      <Typography
                        variant="body2"
                        fontWeight={600}
                        sx={{ color: txn.transaction_type === 'expense' ? 'error.main' : 'success.main' }}
                      >
                        {txn.transaction_type === 'expense' ? '-' : '+'}${txn.amount.toFixed(2)}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              )}
              <Divider sx={{ my: 2 }} />
              <Button component={RouterLink} to="/transactions" size="small">
                View all transactions →
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Container>
  )
}

export default Dashboard
