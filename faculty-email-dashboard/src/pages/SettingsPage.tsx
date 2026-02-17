import React, { useEffect, useState } from 'react'
import { Card, CardContent, Typography, TextField, Button, Box, Alert, CircularProgress, Divider, Grid, Chip } from '@mui/material'
import { api } from '../services/api'
import { useAuth } from '../hooks/useAuth'

interface MailboxStatus {
  connected: boolean
  method?: 'gmail' | 'imap'
  mailbox_email?: string
  last_sync?: string
}

interface QuickStats {
  total: number
  spam: number
  ham: number
  topics: number
}

export function SettingsPage() {
  const { email: userEmail, fullName } = useAuth()
  const [status, setStatus] = useState<MailboxStatus | null>(null)
  const [stats, setStats] = useState<QuickStats | null>(null)
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
      const [mailboxRes, emailsRes] = await Promise.all([
        api.get<MailboxStatus>('/mailbox/status'),
        api.get<{ total: number; emails: { spam_label: string; topic: string }[] }>('/emails/', { params: { page: 1, page_size: 1 } }),
      ])
      setStatus(mailboxRes.data)
      const total = emailsRes.data.total || 0
      // We'll fetch a broader set to compute stats
      if (total > 0) {
        const metricsRes = await api.get<{ total_emails: number; spam_count: number; top_topics: { name: string }[] }>('/dashboard/metrics')
        setStats({
          total: metricsRes.data.total_emails,
          spam: metricsRes.data.spam_count,
          ham: metricsRes.data.total_emails - metricsRes.data.spam_count,
          topics: metricsRes.data.top_topics?.length || 0,
        })
      } else {
        setStats({ total: 0, spam: 0, ham: 0, topics: 0 })
      }
    } catch (e: unknown) {
      const res = e as { response?: { status?: number } }
      if (res?.response?.status === 404) {
        setStatus({ connected: false })
        setError('Mailbox API not available. Restart the backend.')
      } else {
        setError('Failed to load settings')
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
        setError('Mailbox API not available. Restart the backend.')
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
      if (status?.method === 'gmail') {
        const { data } = await api.post<{ new_saved: number }>('/emails/sync', null, { params: { max_emails: 50 }, timeout: 90000 })
        setSuccess(`Gmail sync complete. ${data.new_saved} new emails saved.`)
      } else {
        const { data } = await api.post<{ fetched: number; new_saved: number }>('/mailbox/sync', null, { params: { max_emails: 50 } })
        setSuccess(`Synced: ${data.fetched} fetched, ${data.new_saved} new.`)
      }
      loadStatus()
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
    } catch {
      setError('Failed to disconnect')
    }
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress sx={{ color: '#00d9ff' }} />
      </Box>
    )
  }

  const connectedViaGmail = status?.connected && status?.method === 'gmail'
  const connectedViaImap = status?.connected && status?.method === 'imap'

  const cardSx = {
    border: '1px solid rgba(0, 217, 255, 0.2)',
    borderRadius: 3,
    background: 'rgba(26, 31, 58, 0.5)',
    backdropFilter: 'blur(10px)',
    mb: 3,
  }

  return (
    <Box sx={{ maxWidth: 700 }}>
      <Typography variant="h5" gutterBottom sx={{ fontFamily: '"Playfair Display", serif', color: '#f8f6f0' }}>
        Settings
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>{success}</Alert>}

      {/* Account info */}
      <Card sx={cardSx}>
        <CardContent>
          <Typography variant="h6" sx={{ fontFamily: '"Playfair Display", serif', color: '#f8f6f0', mb: 2 }}>Account</Typography>
          <Grid container spacing={2}>
            <Grid item xs={6}>
              <Typography variant="caption" sx={{ color: '#e8e6e1', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Email</Typography>
              <Typography sx={{ color: '#f8f6f0' }}>{userEmail || '—'}</Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="caption" sx={{ color: '#e8e6e1', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Name</Typography>
              <Typography sx={{ color: '#f8f6f0' }}>{fullName || '—'}</Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="caption" sx={{ color: '#e8e6e1', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Connection</Typography>
              <Box sx={{ mt: 0.5 }}>
                {connectedViaGmail && <Chip label="Google OAuth" size="small" sx={{ background: 'rgba(0,217,255,0.15)', color: '#00d9ff' }} />}
                {connectedViaImap && <Chip label="IMAP" size="small" sx={{ background: 'rgba(255,215,0,0.15)', color: '#ffd700' }} />}
                {!status?.connected && <Chip label="Not connected" size="small" sx={{ background: 'rgba(239,83,80,0.15)', color: '#ef5350' }} />}
              </Box>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="caption" sx={{ color: '#e8e6e1', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Mailbox Email</Typography>
              <Typography sx={{ color: '#f8f6f0' }}>{status?.mailbox_email || '—'}</Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Quick stats */}
      {stats && stats.total > 0 && (
        <Card sx={cardSx}>
          <CardContent>
            <Typography variant="h6" sx={{ fontFamily: '"Playfair Display", serif', color: '#f8f6f0', mb: 2 }}>Inbox Summary</Typography>
            <Grid container spacing={2}>
              {[
                { label: 'Total Emails', value: stats.total, color: '#00d9ff' },
                { label: 'Spam', value: stats.spam, color: '#ef5350' },
                { label: 'Ham (Good)', value: stats.ham, color: '#2e7d32' },
                { label: 'Topics Found', value: stats.topics, color: '#ffd700' },
              ].map((s, i) => (
                <Grid item xs={3} key={i} sx={{ textAlign: 'center' }}>
                  <Typography sx={{ fontFamily: '"Playfair Display", serif', fontSize: '1.5rem', fontWeight: 800, color: s.color }}>
                    {s.value.toLocaleString()}
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#e8e6e1' }}>{s.label}</Typography>
                </Grid>
              ))}
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* Email connection */}
      <Card sx={cardSx}>
        <CardContent>
          <Typography variant="h6" sx={{ fontFamily: '"Playfair Display", serif', color: '#f8f6f0', mb: 1 }}>
            {connectedViaGmail ? 'Gmail Connection' : connectedViaImap ? 'IMAP Connection' : 'Connect Email'}
          </Typography>
          <Typography variant="body2" sx={{ mb: 2, color: '#e8e6e1' }}>
            {connectedViaGmail
              ? 'Emails synced via Gmail API — no app password needed.'
              : status?.connected
                ? 'IMAP mailbox connected.'
                : 'Use "Sign in with Gmail" on the Login page, or connect IMAP below.'}
          </Typography>

          {status?.connected ? (
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              <Button variant="contained" onClick={handleSync} disabled={syncLoading}
                sx={{ background: 'linear-gradient(135deg, #00d9ff 0%, #0099cc 100%)', color: '#0a0e27', fontWeight: 700 }}>
                {syncLoading ? 'Syncing…' : 'Sync now'}
              </Button>
              {connectedViaImap && (
                <Button variant="outlined" color="secondary" onClick={handleDisconnect}>Disconnect</Button>
              )}
            </Box>
          ) : (
            <>
              <Divider sx={{ my: 2, borderColor: 'rgba(0,217,255,0.15)' }} />
              <Typography variant="subtitle2" sx={{ color: '#e8e6e1', mb: 1 }}>Connect via IMAP (App Password)</Typography>
              <form onSubmit={handleConnect}>
                <TextField fullWidth label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} margin="normal" required placeholder="you@gmail.com" size="small" />
                <TextField fullWidth label="App password" type="password" value={appPassword} onChange={(e) => setAppPassword(e.target.value)} margin="normal" required placeholder="16-character App Password" size="small"
                  helperText="Gmail: enable 2-Step Verification → create App Password at myaccount.google.com/apppasswords" />
                <Button type="submit" variant="contained" sx={{ mt: 1 }} disabled={connectLoading}>
                  {connectLoading ? 'Connecting…' : 'Connect'}
                </Button>
              </form>
            </>
          )}
        </CardContent>
      </Card>
    </Box>
  )
}
