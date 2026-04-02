import React, { useCallback, useEffect, useState } from 'react'
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
  Switch,
  FormControlLabel,
} from '@mui/material'
import RefreshIcon from '@mui/icons-material/Refresh'
import HubIcon from '@mui/icons-material/Hub'
import { api } from '../services/api'
import { LoadingSpinner } from '../components/Common/LoadingSpinner'
import type { PipelineEmail, PipelineEmailsResponse } from '../types/pipeline.types'

const cardSx = {
  border: '1px solid rgba(0, 217, 255, 0.2)',
  borderRadius: 3,
  background: 'rgba(26, 31, 58, 0.5)',
  backdropFilter: 'blur(10px)',
}

export function PipelinePage() {
  const [items, setItems] = useState<PipelineEmail[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [live, setLive] = useState(true)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [publishBusy, setPublishBusy] = useState<null | 'sample' | 'gmail' | 'synced'>(null)
  /** When on, list API returns only rows tagged ``mailbox`` (Gmail / saved inbox). */
  const [mailboxOnly, setMailboxOnly] = useState(false)

  const load = useCallback(async () => {
    try {
      setError(null)
      const params: Record<string, string | number> = { limit: 100 }
      if (mailboxOnly) params.pipeline_source = 'mailbox'
      const { data } = await api.get<PipelineEmailsResponse>('/pipeline/emails', { params })
      setItems(data.items ?? [])
    } catch (e: unknown) {
      let msg = 'Failed to load pipeline emails (is PostgreSQL running and is the consumer writing?)'
      if (e && typeof e === 'object' && 'response' in e) {
        const res = (e as { response?: { status?: number; data?: { detail?: unknown } } }).response
        const data = res?.data
        if (data?.detail != null) msg = String(data.detail)
        if (res?.status === 404) {
          msg = `${msg} — If this says "Not Found", restart the FastAPI server from the latest code (route /api/v1/pipeline/emails) and check VITE_API_URL includes /api/v1.`
        }
      }
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [mailboxOnly])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (!live) return
    const t = window.setInterval(() => void load(), 2500)
    return () => window.clearInterval(t)
  }, [live, load])

  const sendFeedback = async (emailId: string, correctLabel: string) => {
    setBusyId(emailId)
    try {
      await api.post('/pipeline/feedback', { email_id: emailId, correct_label: correctLabel })
      await load()
    } finally {
      setBusyId(null)
    }
  }

  const publishSample = async () => {
    setPublishBusy('sample')
    setError(null)
    try {
      await api.post('/pipeline/publish-sample')
      await load()
    } catch (e: unknown) {
      let msg = 'Could not publish to Kafka'
      if (e && typeof e === 'object' && 'response' in e) {
        const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
        if (d != null) msg = String(d)
      }
      setError(msg)
    } finally {
      setPublishBusy(null)
    }
  }

  const publishRealMailbox = async (source: 'gmail' | 'synced') => {
    setPublishBusy(source)
    setError(null)
    try {
      await api.post('/pipeline/publish-mailbox', {}, { params: { source, max_emails: 40 } })
      await load()
    } catch (e: unknown) {
      let msg = 'Could not publish mailbox to Kafka'
      if (e && typeof e === 'object' && 'response' in e) {
        const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
        if (d != null) msg = String(d)
      }
      setError(msg)
    } finally {
      setPublishBusy(null)
    }
  }

  if (loading && items.length === 0) return <LoadingSpinner />

  return (
    <Box sx={{ p: 3, maxWidth: 1400, mx: 'auto' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3, flexWrap: 'wrap' }}>
        <HubIcon sx={{ color: '#00d9ff', fontSize: 36 }} />
        <Box sx={{ flex: 1, minWidth: 200 }}>
          <Typography variant="h5" sx={{ color: '#f8f6f0', fontWeight: 600 }}>
            Live classification pipeline
          </Typography>
          <Typography variant="body2" sx={{ color: 'rgba(248, 246, 240, 0.7)', mt: 0.5 }}>
            The consumer must be running. Use real mail (Gmail or saved inbox) or a demo sample. Rows use a stable ID
            derived from each message so re-publish is safe.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, alignItems: 'center' }}>
          <Button
            variant="contained"
            disabled={publishBusy !== null}
            onClick={() => void publishRealMailbox('gmail')}
            sx={{
              background: 'linear-gradient(135deg, #ea4335 0%, #fbbc04 100%)',
              color: '#0a0e27',
              fontWeight: 700,
              whiteSpace: 'nowrap',
            }}
          >
            {publishBusy === 'gmail' ? 'Publishing…' : 'Gmail → Kafka (40)'}
          </Button>
          <Button
            variant="contained"
            disabled={publishBusy !== null}
            onClick={() => void publishRealMailbox('synced')}
            sx={{
              background: 'linear-gradient(135deg, #34a853 0%, #00d9ff 100%)',
              color: '#0a0e27',
              fontWeight: 700,
              whiteSpace: 'nowrap',
            }}
          >
            {publishBusy === 'synced' ? 'Publishing…' : 'Saved inbox → Kafka (40)'}
          </Button>
          <Button
            variant="outlined"
            disabled={publishBusy !== null}
            onClick={() => void publishSample()}
            sx={{ borderColor: 'rgba(0, 217, 255, 0.5)', color: '#00d9ff', fontWeight: 700 }}
          >
            {publishBusy === 'sample' ? 'Sending…' : 'Demo sample'}
          </Button>
        </Box>
        <FormControlLabel
          control={<Switch checked={mailboxOnly} onChange={(_, v) => setMailboxOnly(v)} color="secondary" />}
          label={<Typography sx={{ color: '#e8e6e1' }}>Mailbox only</Typography>}
        />
        <FormControlLabel
          control={<Switch checked={live} onChange={(_, v) => setLive(v)} color="primary" />}
          label={<Typography sx={{ color: '#e8e6e1' }}>Auto-refresh</Typography>}
        />
        <Tooltip title="Refresh now">
          <IconButton onClick={() => void load()} sx={{ color: '#00d9ff' }} aria-label="refresh">
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Box>

      {error && (
        <Typography sx={{ color: '#ff8a80', mb: 2 }} variant="body2">
          {error}
        </Typography>
      )}

      <Card sx={cardSx}>
        <CardContent sx={{ p: 0 }}>
          <Table size="small" sx={{ '& td, & th': { borderColor: 'rgba(0, 217, 255, 0.15)', color: '#e8e6e1' } }}>
            <TableHead>
              <TableRow>
                <TableCell>Time</TableCell>
                <TableCell>Source</TableCell>
                <TableCell>Text (preview)</TableCell>
                <TableCell>Predicted</TableCell>
                <TableCell align="right">Confidence</TableCell>
                <TableCell>Your feedback</TableCell>
                <TableCell align="right">Correct</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7}>
                    <Typography variant="body2" sx={{ color: 'rgba(248,246,240,0.6)', py: 2 }}>
                      {mailboxOnly
                        ? 'No mailbox-tagged rows yet. Click Gmail → Kafka or Saved inbox → Kafka, or turn off Mailbox only.'
                        : 'No rows yet. Start Zookeeper, Kafka, and the consumer; then publish mail or a demo.'}
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                items.map((row) => (
                  <TableRow key={row.email_id} hover>
                    <TableCell sx={{ whiteSpace: 'nowrap', maxWidth: 120 }}>{row.timestamp ?? '—'}</TableCell>
                    <TableCell sx={{ whiteSpace: 'nowrap' }}>
                      <Chip
                        size="small"
                        label={row.pipeline_source ?? '—'}
                        color={row.pipeline_source === 'mailbox' ? 'success' : row.pipeline_source === 'synthetic' ? 'warning' : 'default'}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell sx={{ maxWidth: 420 }}>
                      <Typography variant="body2" noWrap title={row.text}>
                        {row.text}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip label={row.predicted_label} size="small" color={row.predicted_label === 'spam' ? 'warning' : 'default'} />
                    </TableCell>
                    <TableCell align="right">
                      {row.confidence != null ? `${(row.confidence * 100).toFixed(1)}%` : '—'}
                    </TableCell>
                    <TableCell>
                      {row.feedback ? <Chip label={row.feedback} size="small" variant="outlined" /> : '—'}
                    </TableCell>
                    <TableCell align="right">
                      <Button
                        size="small"
                        variant="outlined"
                        disabled={busyId === row.email_id}
                        onClick={() => void sendFeedback(row.email_id, 'spam')}
                        sx={{ mr: 0.5, borderColor: 'rgba(255, 152, 0, 0.5)', color: '#ffb74d' }}
                      >
                        spam
                      </Button>
                      <Button
                        size="small"
                        variant="outlined"
                        disabled={busyId === row.email_id}
                        onClick={() => void sendFeedback(row.email_id, 'not_spam')}
                        sx={{ borderColor: 'rgba(0, 217, 255, 0.5)', color: '#00d9ff' }}
                      >
                        not spam
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </Box>
  )
}
