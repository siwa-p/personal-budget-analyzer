import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Box, Button, Container, TextField, Typography } from '@mui/material'
import { useForm } from 'react-hook-form'

type LoginValues = {
  email: string
  password: string
}

const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function Login() {
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const { register, handleSubmit } = useForm<LoginValues>({
    defaultValues: { email: '', password: '' }
  })

  const onSubmit = async (values: LoginValues) => {
    setIsLoading(true)
    setError(null)
    try {
      const body = new URLSearchParams()
      body.set('username', values.email)
      body.set('password', values.password)

      const response = await fetch(`${apiUrl}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: body.toString()
      })

      if (!response.ok) {
        const data = await response.json().catch(() => null)
        const message = data?.detail || 'Credenciales invalidas.'
        throw new Error(message)
      }

      const data = (await response.json()) as { access_token: string; token_type: string }
      localStorage.setItem('access_token', data.access_token)
      navigate('/profile')
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : 'Error desconocido.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Container maxWidth="sm" sx={{ py: 6 }}>
      <Typography variant="h4" sx={{ mb: 2, fontWeight: 600 }}>
        Iniciar sesion
      </Typography>
      <Typography sx={{ mb: 3, color: 'text.secondary' }}>
        Usa tu email y password para obtener el token.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Box component="form" onSubmit={handleSubmit(onSubmit)} sx={{ display: 'grid', gap: 2 }}>
        <TextField
          label="Email"
          type="email"
          placeholder="usuario@correo.com"
          InputLabelProps={{ shrink: true }}
          {...register('email', { required: true })}
        />
        <TextField
          label="Password"
          type="password"
          placeholder="Tu password"
          InputLabelProps={{ shrink: true }}
          {...register('password', { required: true })}
        />
        <Button type="submit" variant="contained" disabled={isLoading}>
          Entrar
        </Button>
      </Box>
    </Container>
  )
}

export default Login
