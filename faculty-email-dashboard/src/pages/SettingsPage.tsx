import React, { useEffect, useState } from 'react'
import { Card, CardContent, Typography, TextField, Button, Box, Alert, CircularProgress } from '@mui/material'
import { api } from '../services/api'

interface MailboxStatus {
  connected: boolean
  mailbox_email?: string
  last_sync?: string
}

export function SettingsPage() {
  const [status, setStatus] = useState<MailboxStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [connectLoading, setConnectLoading] = useState(false)
  const [syncLoading, setSyncLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [email, setEmail] = useState('')
  const [appPassword, setAppPassword] = useState('')

  const loadStatus = async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.get<MailboxStatus>('/mailbox/status')
      setStatus(data)
    } catch (e: unknown) {
      const res = e as { response?: { status?: number } }
      // 404 = mailbox API not available (backend not restarted); treat as not connected
      if (res?.response?.status === 404) {
        setStatus({ connected: false })
        setError('Mailbox API not available. Restart the backend: in email-api run "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"')
      } else {
        setError('Failed to load mailbox status')
        setStatus({ connected: false })
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadStatus()
  }, [])

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault()
    setConnectLoading(true)
    setError(null)
    setSuccess(null)
    try {
      await api.post('/mailbox/connect', { email: email.trim(), app_password: appPassword })
      setSuccess('Mailbox connected. Click "Sync now" to fetch your emails.')
      setEmail('')
      setAppPassword('')
      loadStatus()
    } catch (err: unknown) {
      const res = err as { response?: { status?: number; data?: { detail?: string | unknown[] } }; message?: string }
      if (res?.response?.status === 404) {
        setError('Mailbox API not available. Restart the backend from the email-api folder (see RUN.md).')
      } else {
        const data = res?.response?.data as { detail?: string | { msg?: string }[] } | undefined
        let msg = typeof data?.detail === 'string' ? data.detail : null
        if (!msg && Array.isArray(data?.detail) && data.detail[0]?.msg) msg = data.detail[0].msg
        if (!msg && res?.message) msg = res.message
        setError(msg || 'Connection failed. For Gmail use an App Password (Security → 2-Step Verification → App passwords).')
      }
    } finally {
      setConnectLoading(false)
    }
  }

  const handleSync = async () => {
    setSyncLoading(true)
    setError(null)
    setSuccess(null)
    try {
      const { data } = await api.post<{ fetched: number; new_saved: number }>('/mailbox/sync', null, { params: { max_emails: 50 } })
      setSuccess(`Synced: ${data.fetched} emails fetched, ${data.new_saved} new. Check the Emails page.`)
    } catch (err: unknown) {
      const res = err as { response?: { data?: { detail?: string } } }
      setError(res?.response?.data?.detail || 'Sync failed')
    } finally {
      setSyncLoading(false)
    }
  }

  const handleDisconnect = async () => {
    setError(null)
    setSuccess(null)
    try {
      await api.delete('/mailbox/disconnect')
      setSuccess('Mailbox disconnected.')
      loadStatus()
    } catch (e) {
      setError('Failed to disconnect')
    }
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box sx={{ maxWidth: 600 }}>
      <Typography variant="h5" gutterBottom>Real-time email (IMAP)</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Connect your Gmail or Outlook to sync and classify real emails. Gmail: use an App Password (not your normal password).
      </Typography>
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>{success}</Alert>}

      {status?.connected ? (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="subtitle1">Connected: {status.mailbox_email}</Typography>
            <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
              <Button variant="contained" onClick={handleSync} disabled={syncLoading}>
                {syncLoading ? 'Syncing…' : 'Sync now'}
              </Button>
              <Button variant="outlined" color="secondary" onClick={handleDisconnect}>Disconnect</Button>
            </Box>
          </CardContent>
        </Card>
      ) : (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="subtitle1" gutterBottom>Connect mailbox</Typography>
            <form onSubmit={handleConnect}>
              <TextField fullWidth label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} margin="normal" required placeholder="you@gmail.com" />
              <TextField fullWidth label="App password" type="password" value={appPassword} onChange={(e) => setAppPassword(e.target.value)} margin="normal" required placeholder="16-character App Password (no spaces)" helperText="Gmail: enable 2-Step Verification, then create one at myaccount.google.com/apppasswords — use the 16-character password without spaces." />
              <Button type="submit" variant="contained" sx={{ mt: 2 }} disabled={connectLoading}>
                {connectLoading ? 'Connecting…' : 'Connect'}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent>
          <Typography variant="h6">Settings</Typography>
          <Typography variant="body2" color="text.secondary">Notification and display preferences can be configured here.</Typography>
        </CardContent>
      </Card>
    </Box>
  )
}
