import { useContext, useEffect, useState } from 'react'
import { Link as RouterLink } from 'react-router-dom'
import {
  Alert,
  Box,
  Button,
  Container,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  TextField,
  Typography
} from '@mui/material'
import { Controller, useForm } from 'react-hook-form'
import { ThemeContext } from '../contexts/ThemeContext'

type ProfileFormValues = {
  username: string
  email: string
  full_name?: string | null
  theme: string
}

const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function Profile() {
  const { setTheme } = useContext(ThemeContext)
  const [token] = useState(() => localStorage.getItem('access_token') || '')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const { register, handleSubmit, reset, control } = useForm<ProfileFormValues>({
    defaultValues: {
      username: '',
      email: '',
      full_name: '',
      theme: 'light'
    }
  })

  const loadProfile = async (authToken: string) => {
    if (!authToken) {
      setError('Add your token to load the profile.')
      return
    }
    setIsLoading(true)
    setError(null)
    setSuccess(null)
    try {
      const response = await fetch(`${apiUrl}/api/v1/users/me`, {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      })
      if (!response.ok) {
        throw new Error('Failed to load the profile. Verify your token or try again later.')
      }
      const data = (await response.json()) as ProfileFormValues
      reset({
        username: data.username,
        email: data.email,
        full_name: data.full_name ?? '',
        theme: data.theme ?? 'light'
      })
      if (data.theme === 'dark' || data.theme === 'light') {
        setTheme(data.theme)
      }
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : 'Unknown error.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (token) {
      loadProfile(token)
    }
  }, [token])

  const onSubmit = async (values: ProfileFormValues) => {
    if (!token) {
      setError('You must be logged in to update your profile.')
      return
    }
    setIsLoading(true)
    setError(null)
    setSuccess(null)
    try {
      const response = await fetch(`${apiUrl}/api/v1/users/me`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(values)
      })
      if (!response.ok) {
        const message = await response.text()
        throw new Error(message || 'Failed to update the profile.')
      }
      const data = (await response.json()) as ProfileFormValues
      reset({
        username: data.username,
        email: data.email,
        full_name: data.full_name ?? '',
        theme: data.theme ?? values.theme
      })
      if (data.theme === 'dark' || data.theme === 'light') {
        setTheme(data.theme)
      }
      setSuccess('Profile updated successfully.')
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : 'Unknown error.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Container maxWidth="sm" sx={{ py: 6 }}>
      <Typography variant="h4" sx={{ mb: 3, fontWeight: 600 }}>
        Update Profile
      </Typography>

      {!token && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          You must be logged in to update your profile.
          <Button
            component={RouterLink}
            to="/login"
            size="small"
            sx={{ ml: 2 }}
            variant="outlined"
          >
            Go to login
          </Button>
        </Alert>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          {success}
        </Alert>
      )}

      <Box component="form" onSubmit={handleSubmit(onSubmit)} sx={{ display: 'grid', gap: 2 }}>
        <TextField
          label="Username"
          placeholder="Ej. admin"
          InputLabelProps={{ shrink: true }}
          {...register('username', { required: true })}
          disabled={isLoading || !token}
        />
        <TextField
          label="Email"
          type="email"
          placeholder="example@email.com"
          InputLabelProps={{ shrink: true }}
          {...register('email', { required: true })}
          disabled={isLoading || !token}
        />
        <TextField
          label="Full Name"
          placeholder="Example: Ana Gomez"
          InputLabelProps={{ shrink: true }}
          {...register('full_name')}
          disabled={isLoading || !token}
        />

        <FormControl>
          <InputLabel id="theme-label">Theme</InputLabel>
          <Controller
            name="theme"
            control={control}
            rules={{ required: true }}
            render={({ field }) => (
              <Select
                labelId="theme-label"
                label="Theme"
                value={field.value}
                {...field}
                disabled={isLoading || !token}
              >
                <MenuItem value="light">Light</MenuItem>
                <MenuItem value="dark">Dark</MenuItem>
              </Select>
            )}
          />
        </FormControl>

        <Button type="submit" variant="contained" disabled={isLoading || !token}>
          Save changes
        </Button>
      </Box>
    </Container>
  )
}

export default Profile
