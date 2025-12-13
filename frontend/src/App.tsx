import { useState, useEffect } from 'react'
import { Box } from '@mui/material'

function App() {
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
    <Box sx={{ p: 4 }}>
      <h1>hello world</h1>

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
    </Box>
  )
}

export default App
