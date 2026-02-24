import { useEffect, useMemo, useState } from 'react'
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

type TransactionFormValues = {
  amount: number
  transaction_date: string
  description: string
  category_id: number
}

type Category = {
  id: number
  name: string
  type: 'income' | 'expense'
  is_active: boolean
}

const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function AddTransaction() {
  const [token] = useState(() => localStorage.getItem('access_token') || '')
  const [categories, setCategories] = useState<Category[]>([])
  const [isLoadingCategories, setIsLoadingCategories] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const { register, handleSubmit, reset, control, watch } = useForm<TransactionFormValues>({
    defaultValues: {
      amount: 0,
      transaction_date: new Date().toISOString().slice(0, 10),
      description: '',
      category_id: 0
    }
  })

  const selectedCategoryId = watch('category_id')
  const selectedCategory = useMemo(
    () => categories.find((category) => category.id === selectedCategoryId),
    [categories, selectedCategoryId]
  )

  useEffect(() => {
    const loadCategories = async () => {
      if (!token) {
        return
      }
      setIsLoadingCategories(true)
      setError(null)
      try {
        const [userResponse, systemResponse] = await Promise.all([
          fetch(`${apiUrl}/api/v1/categories`, {
            headers: { Authorization: `Bearer ${token}` }
          }),
          fetch(`${apiUrl}/api/v1/categories/system`, {
            headers: { Authorization: `Bearer ${token}` }
          })
        ])

        if (!userResponse.ok && !systemResponse.ok) {
          throw new Error('Failed to load categories.')
        }

        const userCategories = userResponse.ok ? ((await userResponse.json()) as Category[]) : []
        const systemCategories = systemResponse.ok ? ((await systemResponse.json()) as Category[]) : []
        const uniqueCategories = Array.from(
          new Map([...userCategories, ...systemCategories].map((category) => [category.id, category])).values()
        )
        setCategories(uniqueCategories.filter((category) => category.is_active))
      } catch (fetchError) {
        setError(fetchError instanceof Error ? fetchError.message : 'Unknown error loading categories.')
      } finally {
        setIsLoadingCategories(false)
      }
    }

    loadCategories()
  }, [token])

  const onSubmit = async (values: TransactionFormValues) => {
    if (!token) {
      setError('You must be logged in to add transactions.')
      return
    }
    const category = categories.find((item) => item.id === values.category_id)
    if (!category) {
      setError('Select a valid category.')
      return
    }

    setIsSubmitting(true)
    setError(null)
    setSuccess(null)

    try {
      const response = await fetch(`${apiUrl}/api/v1/transactions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          amount: values.amount,
          transaction_date: values.transaction_date,
          description: values.description || null,
          category_id: values.category_id,
          transaction_type: category.type
        })
      })

      if (!response.ok) {
        const data = await response.json().catch(() => null)
        const message = data?.detail || 'Failed to create transaction.'
        throw new Error(message)
      }

      setSuccess('Transaction added successfully.')
      reset({
        amount: 0,
        transaction_date: new Date().toISOString().slice(0, 10),
        description: '',
        category_id: 0
      })
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : 'Unknown error.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Container maxWidth="sm" sx={{ py: 6 }}>
      <Typography variant="h4" sx={{ mb: 3, fontWeight: 600 }}>
        Add Transaction
      </Typography>

      {!token && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          You must be logged in to add transactions.
          <Button component={RouterLink} to="/login" size="small" sx={{ ml: 2 }} variant="outlined">
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
          label="Amount"
          type="number"
          inputProps={{ step: '0.01', min: 0.01 }}
          InputLabelProps={{ shrink: true }}
          {...register('amount', { required: true, valueAsNumber: true, min: 0.01 })}
          disabled={isSubmitting || !token}
        />

        <TextField
          label="Date"
          type="date"
          InputLabelProps={{ shrink: true }}
          {...register('transaction_date', { required: true })}
          disabled={isSubmitting || !token}
        />

        <TextField
          label="Description"
          placeholder="Optional notes"
          InputLabelProps={{ shrink: true }}
          {...register('description')}
          disabled={isSubmitting || !token}
        />

        <FormControl>
          <InputLabel id="category-label">Category</InputLabel>
          <Controller
            name="category_id"
            control={control}
            rules={{ required: true, min: 1 }}
            render={({ field }) => (
              <Select
                labelId="category-label"
                label="Category"
                {...field}
                disabled={isSubmitting || isLoadingCategories || !token}
              >
                <MenuItem value={0}>Select a category</MenuItem>
                {categories.map((category) => (
                  <MenuItem key={category.id} value={category.id}>
                    {category.name}
                  </MenuItem>
                ))}
              </Select>
            )}
          />
        </FormControl>

        {selectedCategory && (
          <Typography variant="body2" color="text.secondary">
            Transaction type inferred from category: {selectedCategory.type}
          </Typography>
        )}

        <Button type="submit" variant="contained" disabled={isSubmitting || isLoadingCategories || !token}>
          {isSubmitting ? 'Saving...' : 'Add transaction'}
        </Button>
      </Box>
    </Container>
  )
}

export default AddTransaction
