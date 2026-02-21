import React, { useState, useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Box, Card, CardContent, TextField, Button, Typography, Alert, Divider } from '@mui/material'
import { api } from '../services/api'
import { useDispatch } from 'react-redux'
import { setUser } from '../store/slices/userSlice'

function getEmailFromToken(token: string): string {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return (payload.sub as string) || ''
  } catch {
    return ''
  }
}

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const [searchParams, setSearchParams] = useSearchParams()
  const handledRef = useRef(false)

  // Handle callback from Google OAuth: ?token=... or ?error=...
  useEffect(() => {
    const token = searchParams.get('token')
    const err = searchParams.get('error')
    if (err) {
      setError(err === 'access_denied' ? 'Google sign-in was cancelled.' : 'Google sign-in failed. Try again or use email/password.')
      setSearchParams({}, { replace: true })
      return
    }
    if (!token) return
    // Prevent duplicate handling (React StrictMode runs effects twice)
    if (handledRef.current) return
    handledRef.current = true
    localStorage.setItem('access_token', token)
    const userEmail = getEmailFromToken(token)
    dispatch(setUser({ email: userEmail, fullName: userEmail.split('@')[0], token }))
    setSearchParams({}, { replace: true })
    // Go to dashboard immediately so user isn't stuck; sync runs in background
    navigate('/dashboard', { replace: true })
    // Fire-and-forget sync
    api.post('/emails/sync', null, { params: { max_emails: 150 }, timeout: 120000 }).catch(() => {})
  }, [searchParams, dispatch, navigate, setSearchParams])

  const handleGoogleLogin = () => {
    const base = api.defaults.baseURL || '/api/v1'
    window.location.href = `${base}/auth/google`
  }

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
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: 'radial-gradient(ellipse 80% 50% at 50% -20%, rgba(0, 217, 255, 0.12), transparent), #0a0e27' }}>
      <Card sx={{ maxWidth: 400, width: '100%', background: 'rgba(26, 31, 58, 0.6)', backdropFilter: 'blur(10px)', border: '1px solid rgba(0, 217, 255, 0.2)', borderRadius: 3 }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h5" gutterBottom sx={{ fontFamily: '"Playfair Display", serif', fontWeight: 700, color: '#f8f6f0', textAlign: 'center' }}>Faculty & Personal Email</Typography>
          {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}

          <Button
            fullWidth
            variant="contained"
            onClick={handleGoogleLogin}
            sx={{
              mt: 1,
              py: 1.5,
              borderRadius: 50,
              fontWeight: 700,
              background: 'linear-gradient(135deg, #00d9ff 0%, #0099cc 100%)',
              color: '#0a0e27',
              '&:hover': { background: 'linear-gradient(135deg, #00d9ff 0%, #0099cc 100%)', boxShadow: '0 10px 30px rgba(0, 217, 255, 0.35)' },
            }}
          >
            Sign in with Gmail
          </Button>

          <Divider sx={{ my: 2, borderColor: 'rgba(0, 217, 255, 0.3)' }}>
            <Typography variant="caption" sx={{ color: '#e8e6e1' }}>or</Typography>
          </Divider>

          <form onSubmit={handleSubmit}>
            <TextField fullWidth label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} margin="normal" />
            <TextField fullWidth label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} margin="normal" />
            <Button type="submit" fullWidth variant="outlined" sx={{ mt: 2, py: 1.5, borderRadius: 50, fontWeight: 700 }} disabled={loading}>
              {loading ? 'Signing in…' : 'Sign in with email'}
            </Button>
          </form>
          <Typography variant="caption" display="block" sx={{ mt: 2, color: '#e8e6e1', textAlign: 'center' }}>Demo: faculty@university.edu / faculty123</Typography>
        </CardContent>
      </Card>
    </Box>
  )
}
