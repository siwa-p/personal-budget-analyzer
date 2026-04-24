import { useContext, useState } from 'react'
import { Link as RouterLink, useNavigate } from 'react-router-dom'
import { Alert, Box, Button, TextField, Typography } from '@mui/material'
import { useForm } from 'react-hook-form'
import { ThemeContext } from '../contexts/ThemeContext'

type LoginValues = {
  email: string
  password: string
}

function Login() {
  const navigate = useNavigate()
  const { setTheme } = useContext(ThemeContext)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const { register, handleSubmit } = useForm<LoginValues>({
    defaultValues: { email: '', password: '' }
  })

  const onSubmit = async (values: LoginValues) => {
    setIsLoading(true)
    setError(null)
    try {
      const { signIn, fetchAuthSession } = await import('aws-amplify/auth')
      await signIn({ username: values.email, password: values.password })
      const session = await fetchAuthSession()
      const idToken = session.tokens?.idToken?.toString()
      if (!idToken) throw new Error('No token returned from Cognito.')
      localStorage.setItem('access_token', idToken)
      try {
        const profileResponse = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/users/me`, {
          headers: { Authorization: `Bearer ${idToken}` }
        })
        if (profileResponse.ok) {
          const profile = (await profileResponse.json()) as { theme?: 'light' | 'dark' }
          if (profile.theme === 'dark' || profile.theme === 'light') {
            setTheme(profile.theme)
          }
        }
      } catch {
        // ignore theme sync failures
      }
      navigate('/profile')
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : 'Unknown error.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex' }}>

      {/* Left panel — branding */}
      <Box
        sx={{
          display: { xs: 'none', md: 'flex' },
          flex: 1,
          background: 'linear-gradient(160deg, #0f1f14 0%, #1a3a24 50%, #22472d 100%)',
          color: 'white',
          flexDirection: 'column',
          justifyContent: 'center',
          px: 8,
        }}
      >
        <Typography variant="h2" sx={{ fontWeight: 800, letterSpacing: 1, fontFamily: '"Trebuchet MS", Arial, sans-serif' }}>
          Ledgr
        </Typography>
        <Typography sx={{ mt: 2, fontSize: '1.1rem', color: 'rgba(255,255,255,0.7)', lineHeight: 1.8, maxWidth: 380 }}>
          Track spending, set budgets, and reach your savings goals — all in one place.
        </Typography>
      </Box>

      {/* Right panel — form */}
      <Box
        sx={{
          width: { xs: '100%', md: 480 },
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          px: { xs: 4, md: 8 },
          py: 8,
          backgroundColor: 'background.default',
        }}
      >
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 0.5 }}>
          Welcome back
        </Typography>
        <Typography sx={{ mb: 4, color: 'text.secondary' }}>
          Sign in to your Ledgr account
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        <Box component="form" onSubmit={handleSubmit(onSubmit)} sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
          <TextField
            label="Email"
            type="email"
            fullWidth
            {...register('email', { required: true })}
          />
          <TextField
            label="Password"
            type="password"
            fullWidth
            {...register('password', { required: true })}
          />
          <Button
            type="submit"
            variant="contained"
            fullWidth
            size="large"
            disabled={isLoading}
            sx={{ mt: 1, py: 1.5, borderRadius: 2, fontWeight: 700 }}
          >
            {isLoading ? 'Signing in…' : 'Sign In'}
          </Button>
        </Box>

        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Button component={RouterLink} to="/forgot-password" size="small" sx={{ color: 'text.secondary', textTransform: 'none' }}>
            Forgot password?
          </Button>
          <Typography sx={{ fontSize: '0.9rem', color: 'text.secondary' }}>
            No account?{' '}
            <Button component={RouterLink} to="/register" size="small" sx={{ fontWeight: 600, textTransform: 'none', p: 0, minWidth: 0 }}>
              Register
            </Button>
          </Typography>
        </Box>
      </Box>

    </Box>
  )
}

export default Login
