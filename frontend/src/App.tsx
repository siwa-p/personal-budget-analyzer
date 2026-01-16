import { useEffect, useMemo, useState } from 'react'
import { Link as RouterLink, Route, Routes, useNavigate } from 'react-router-dom'
import { AppBar, Box, Button, Container, CssBaseline, Toolbar, Typography } from '@mui/material'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import Login from './pages/Login'
import Profile from './pages/Profile'
import { ThemeContext } from './contexts/ThemeContext'

function Home() {
  const [isConnected, setIsConnected] = useState(false)

  useEffect(() => {
    const checkApi = async () => {
      try {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
        const response = await fetch(`${apiUrl}/health`)
        if (response.ok) {
          setIsConnected(true)
        } else {
          setIsConnected(false)
        }
      } catch (err) {
        setIsConnected(false)
      }
    }

    checkApi()
  }, [])

  return (
    <Container sx={{ py: 6 }}>
      <Typography variant="h4" sx={{ fontWeight: 600 }}>
        Personal Budget Analyzer
      </Typography>
      <Typography sx={{ mt: 1, color: 'text.secondary' }}>
        This is a personal budget analyzer.
      </Typography>

      <Box
        sx={{
          mt: 2,
          p: 2,
          backgroundColor: isConnected ? '#4caf50' : '#f44336',
          color: 'white',
          borderRadius: 1,
          display: 'inline-block',
          fontWeight: 'bold'
        }}
      >
        {isConnected ? 'connected' : 'disconnected'}
      </Box>
    </Container>
  )
}

function App() {
  const navigate = useNavigate()
  const [themeMode, setThemeMode] = useState<'light' | 'dark'>(
    () => (localStorage.getItem('theme') as 'light' | 'dark') || 'light'
  )
  const hasToken = Boolean(localStorage.getItem('access_token'))

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    setThemeMode('light')
    localStorage.setItem('theme', 'light')
    navigate('/login')
  }

  const theme = useMemo(
    () =>
      createTheme({
        palette: {
          mode: themeMode,
          background: {
            default: themeMode === 'dark' ? '#0b0d12' : '#f5f6f8',
            paper: themeMode === 'dark' ? '#141821' : '#ffffff'
          }
        }
      }),
    [themeMode]
  )

  const setTheme = (mode: 'light' | 'dark') => {
    setThemeMode(mode)
    localStorage.setItem('theme', mode)
  }

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      return
    }
    const fetchTheme = async () => {
      try {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
        const response = await fetch(`${apiUrl}/api/v1/users/me`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        if (!response.ok) {
          return
        }
        const data = (await response.json()) as { theme?: 'light' | 'dark' }
        if (data.theme) {
          setTheme(data.theme)
        }
      } catch {
        // ignore theme sync failures
      }
    }
    fetchTheme()
  }, [])

  return (
    <ThemeContext.Provider value={{ theme: themeMode, setTheme }}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Box sx={{ minHeight: '100vh', backgroundColor: 'background.default' }}>
          <AppBar position="static" color="transparent" elevation={0} sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Toolbar sx={{ gap: 2 }}>
              <Typography variant="h6" sx={{ flexGrow: 1 }}>
                Smore Budget
              </Typography>
              <Button component={RouterLink} to="/" color="inherit">
                Home
              </Button>
              <Button component={RouterLink} to="/profile" color="inherit">
                Profile
              </Button>
              {hasToken ? (
                <Button onClick={handleLogout} color="inherit">
                  Logout
                </Button>
              ) : (
                <Button component={RouterLink} to="/login" color="inherit">
                  Login
                </Button>
              )}
            </Toolbar>
          </AppBar>

          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="/login" element={<Login />} />
          </Routes>
        </Box>
      </ThemeProvider>
    </ThemeContext.Provider>
  )
}

export default App
