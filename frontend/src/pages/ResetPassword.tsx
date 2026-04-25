import { useState } from 'react'
import { Link as RouterLink, useLocation, useNavigate } from 'react-router-dom'
import { Alert, Box, Button, Container, TextField, Typography } from '@mui/material'
import { useForm } from 'react-hook-form'

type ResetPasswordValues = {
    email: string
    code: string
    newPassword: string
    confirmPassword: string
}

function ResetPassword() {
    const navigate = useNavigate()
    const location = useLocation()
    const prefillEmail = (location.state as { email?: string } | null)?.email ?? ''
    const [error, setError] = useState<string | null>(null)
    const [success, setSuccess] = useState<string | null>(null)
    const [isLoading, setIsLoading] = useState(false)

    const { register, handleSubmit } = useForm<ResetPasswordValues>({
        defaultValues: { email: prefillEmail, code: '', newPassword: '', confirmPassword: '' }
    })

    const onSubmit = async (values: ResetPasswordValues) => {
        if (values.newPassword !== values.confirmPassword) {
            setError('Passwords do not match.')
            return
        }
        setIsLoading(true)
        setError(null)
        setSuccess(null)
        try {
            const { confirmResetPassword } = await import('aws-amplify/auth')
            await confirmResetPassword({
                username: values.email,
                confirmationCode: values.code,
                newPassword: values.newPassword,
            })
            setSuccess('Password updated successfully.')
            setTimeout(() => navigate('/login'), 2000)
        } catch (fetchError) {
            setError(fetchError instanceof Error ? fetchError.message : 'Unknown error.')
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <Box
            sx={{
                minHeight: 'calc(100vh - 64px)',
                background: 'radial-gradient(circle at 20% 20%, #8dbb5f 0%, #4f7a39 45%, #2b4b2a 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                px: 2,
                py: 6
            }}
        >
            <Container maxWidth="xs">
                <Box
                    sx={{
                        textAlign: 'center',
                        color: 'white',
                        fontFamily: '"Trebuchet MS", "Lucida Sans Unicode", "Lucida Grande", Arial, sans-serif'
                    }}
                >
                    <Box
                        sx={{
                            width: 48,
                            height: 48,
                            borderRadius: '50%',
                            border: '2px solid rgba(255,255,255,0.6)',
                            mx: 'auto',
                            mb: 2,
                            display: 'grid',
                            placeItems: 'center',
                            fontWeight: 700
                        }}
                    >
                        PB
                    </Box>
                    <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
                        Ledgr
                    </Typography>
                    <Typography sx={{ mb: 4, opacity: 0.9 }}>
                        Reset Password
                    </Typography>

                    {error && (
                        <Alert severity="error" sx={{ mb: 2 }}>
                            {error}
                        </Alert>
                    )}

                    {success && (
                        <Alert severity="success" sx={{ mb: 2 }}>
                            {success} Redirecting to login...
                        </Alert>
                    )}

                    <Box
                        component="form"
                        onSubmit={handleSubmit(onSubmit)}
                        sx={{ display: 'grid', gap: 2, alignItems: 'center', justifyItems: 'center' }}
                    >
                        <TextField
                            label="Email"
                            type="email"
                            InputLabelProps={{ shrink: true, sx: { color: 'black', fontWeight: 700 } }}
                            {...register('email', { required: true })}
                            sx={{ width: 220, backgroundColor: '#e0e0e0', borderRadius: 1, '& .MuiInputBase-input': { color: '#1b1b1b' } }}
                        />
                        <TextField
                            label="6-digit code from email"
                            type="text"
                            InputLabelProps={{ shrink: true, sx: { color: 'black', fontWeight: 700 } }}
                            {...register('code', { required: true })}
                            sx={{ width: 220, backgroundColor: '#e0e0e0', borderRadius: 1, '& .MuiInputBase-input': { color: '#1b1b1b' } }}
                        />
                        <TextField
                            label="New Password"
                            type="password"
                            InputLabelProps={{ shrink: true, sx: { color: 'black', fontWeight: 700 } }}
                            {...register('newPassword', { required: true, minLength: 8 })}
                            sx={{ width: 220, backgroundColor: '#e0e0e0', borderRadius: 1, '& .MuiInputBase-input': { color: '#1b1b1b' } }}
                        />
                        <TextField
                            label="Confirm Password"
                            type="password"
                            InputLabelProps={{ shrink: true, sx: { color: 'black', fontWeight: 700 } }}
                            {...register('confirmPassword', { required: true, minLength: 8 })}
                            sx={{ width: 220, backgroundColor: '#e0e0e0', borderRadius: 1, '& .MuiInputBase-input': { color: '#1b1b1b' } }}
                        />
                        <Button
                            type="submit"
                            variant="contained"
                            disabled={isLoading || success !== null}
                            sx={{ mt: 1, px: 4, borderRadius: 999, backgroundColor: 'primary.main', '&:hover': { backgroundColor: '#5a5a5a' } }}
                        >
                            Reset Password
                        </Button>
                    </Box>

                    <Typography sx={{ mt: 3, fontStyle: 'italic' }}>
                        Remember your password?{' '}
                        <Button
                            component={RouterLink}
                            to="/login"
                            size="small"
                            sx={{ ml: 1, textDecoration: 'underline', color: 'white' }}
                        >
                            Sign In
                        </Button>
                    </Typography>
                </Box>
            </Container>
        </Box>
    )
}

export default ResetPassword
