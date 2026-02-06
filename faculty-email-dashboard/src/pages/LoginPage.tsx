import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Box, Card, CardContent, TextField, Button, Typography, Alert } from '@mui/material'
import { api } from '../services/api'
import { useDispatch } from 'react-redux'
import { setUser } from '../store/slices/userSlice'

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const dispatch = useDispatch()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.append('username', email.trim())
      params.append('password', password)
      const { data } = await api.post('/auth/login', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      const token = data?.access_token
      if (token) {
        dispatch(setUser({ email: email.trim(), fullName: email.split('@')[0], token }))
        navigate('/dashboard', { replace: true })
      } else {
        setError('Invalid response from server')
      }
    } catch (err: unknown) {
      const res = err as { response?: { data?: { detail?: string | string[] } }; message?: string }
      if (!res?.response && res?.message) {
        setError('Cannot reach server. Is the backend running on port 8000?')
        return
      }
      const detail = res?.response?.data?.detail
      const message = Array.isArray(detail) ? detail.join(', ') : (detail || 'Login failed. Check email and password.')
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', bgcolor: 'grey.100' }}>
      <Card sx={{ maxWidth: 400, width: '100%' }}>
        <CardContent>
          <Typography variant="h5" gutterBottom>Faculty & Personal Email Classification</Typography>
          {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
          <form onSubmit={handleSubmit}>
            <TextField fullWidth label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} margin="normal" required />
            <TextField fullWidth label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} margin="normal" required />
            <Button type="submit" fullWidth variant="contained" sx={{ mt: 2 }} disabled={loading}>
              {loading ? 'Signing in…' : 'Sign In'}
            </Button>
          </form>
          <Typography variant="caption" display="block" sx={{ mt: 2 }}>Demo: faculty@university.edu / faculty123</Typography>
        </CardContent>
      </Card>
    </Box>
  )
}
