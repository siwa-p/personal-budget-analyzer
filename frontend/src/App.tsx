import { useState, useEffect } from 'react'
import { Link as RouterLink, Route, Routes, useNavigate } from 'react-router-dom'
import { AppBar, Box, Button, Container, Toolbar, Typography } from '@mui/material'
import Login from './pages/Login'
import Profile from './pages/Profile'

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
        Estado de la API
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
  const hasToken = Boolean(localStorage.getItem('access_token'))

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    navigate('/login')
  }

  return (
    <Box sx={{ minHeight: '100vh', backgroundColor: '#f5f6f8' }}>
      <AppBar position="static" color="transparent" elevation={0} sx={{ borderBottom: '1px solid #e0e0e0' }}>
        <Toolbar sx={{ gap: 2 }}>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Smore Budget
          </Typography>
          <Button component={RouterLink} to="/" color="inherit">
            Inicio
          </Button>
          <Button component={RouterLink} to="/profile" color="inherit">
            Perfil
          </Button>
          {hasToken ? (
            <Button onClick={handleLogout} color="inherit">
              Salir
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
  )
}

export default App
