import { useState } from 'react'
import { Link as RouterLink } from 'react-router-dom'
import { Alert, Box, Button, Container, Typography } from '@mui/material'
import TrendLineGraph from '../components/charts/TrendLineGraph'
import SpendingPieChart from '../components/charts/SpendingPieChart'
import BudgetVsActual from '../components/charts/BudgetVsActual'

function Analytics() {
  const [token] = useState(() => localStorage.getItem('access_token') || '')

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
        </Box>
      )}
    </Container>
  )
}

export default Analytics
