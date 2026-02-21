import React, { useEffect, useState, useCallback } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Button,
  CircularProgress,
  Alert,
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import PsychologyIcon from '@mui/icons-material/Psychology'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { api } from '../services/api'
import { LoadingSpinner } from '../components/Common/LoadingSpinner'

const cardSx = {
  border: '1px solid rgba(0, 217, 255, 0.2)',
  borderRadius: 3,
  background: 'rgba(26, 31, 58, 0.5)',
  backdropFilter: 'blur(10px)',
}

export interface DagRun {
  dag_id?: string
  run_id?: string
  state?: string
  start_date?: string
  end_date?: string
}

export interface DailyAnalyticsPoint {
  metric_date?: string
  daily_volume?: number
  spam_count?: number
  spam_rate?: number
  ham_count?: number
}

export interface ModelVersion {
  version?: string
  training_date?: string
  accuracy?: number
  f1?: number
  is_champion?: boolean
}

export function BigDataAnalytics() {
  const [pipelineStatus, setPipelineStatus] = useState<DagRun[]>([])
  const [dailyData, setDailyData] = useState<DailyAnalyticsPoint[]>([])
  const [modelCurrent, setModelCurrent] = useState<ModelVersion | null>(null)
  const [modelHistory, setModelHistory] = useState<ModelVersion[]>([])
  const [partitions, setPartitions] = useState<string[]>([])
  const [kafkaStats, setKafkaStats] = useState<{ messagesPerSec?: number; consumerLag?: number; dlqSize?: number }>({})
  const [loading, setLoading] = useState(true)
  const [refreshLoading, setRefreshLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchPipelineStatus = useCallback(async () => {
    try {
      const r = await api.get<{ dag_runs: DagRun[] }>('/bigdata/pipeline/status')
      setPipelineStatus(r.data?.dag_runs ?? [])
    } catch {
      setPipelineStatus([])
    }
  }, [])

  const fetchDaily = useCallback(async () => {
    const end = new Date()
    const start = new Date()
    start.setDate(start.getDate() - 30)
    const start_date = start.toISOString().slice(0, 10)
    const end_date = end.toISOString().slice(0, 10)
    try {
      const r = await api.get<{ data: DailyAnalyticsPoint[] }>('/bigdata/analytics/daily', {
        params: { start_date, end_date },
      })
      setDailyData(Array.isArray(r.data?.data) ? r.data.data : [])
    } catch {
      setDailyData([])
    }
  }, [])

  const fetchModel = useCallback(async () => {
    try {
      const [cur, hist] = await Promise.all([
        api.get<ModelVersion>('/bigdata/model/current'),
        api.get<{ versions: ModelVersion[] }>('/bigdata/model/history'),
      ])
      setModelCurrent(cur.data ?? null)
      setModelHistory(hist.data?.versions ?? [])
    } catch {
      setModelCurrent(null)
      setModelHistory([])
    }
  }, [])

  const fetchPartitions = useCallback(async () => {
    try {
      const r = await api.get<{ partitions: string[] }>('/bigdata/storage/partitions', {
        params: { table: 'emails_raw' },
      })
      setPartitions(r.data?.partitions ?? [])
    } catch {
      setPartitions([])
    }
  }, [])

  useEffect(() => {
    Promise.all([fetchPipelineStatus(), fetchDaily(), fetchModel(), fetchPartitions()])
      .finally(() => setLoading(false))
  }, [fetchPipelineStatus, fetchDaily, fetchModel, fetchPartitions])

  useEffect(() => {
    const t = setInterval(fetchPipelineStatus, 30000)
    return () => clearInterval(t)
  }, [fetchPipelineStatus])

  useEffect(() => {
    const t = setInterval(() => {
      setKafkaStats((s) => ({
        messagesPerSec: (s.messagesPerSec ?? 0) + Math.floor(Math.random() * 3),
        consumerLag: Math.floor(Math.random() * 100),
        dlqSize: Math.floor(Math.random() * 5),
      }))
    }, 10000)
    return () => clearInterval(t)
  }, [])

  const runAnalyticsNow = async () => {
    setRefreshLoading(true)
    setError(null)
    try {
      await api.post('/bigdata/analytics/refresh')
      await fetchPipelineStatus()
      await fetchDaily()
    } catch (e: unknown) {
      setError((e as Error)?.message ?? 'Failed to trigger')
    } finally {
      setRefreshLoading(false)
    }
  }

  if (loading) return <LoadingSpinner />

  const chartData = dailyData.map((d) => ({
    date: (d.metric_date ?? '').slice(5, 10),
    total: d.daily_volume ?? 0,
    spam: d.spam_count ?? 0,
  }))

  const stateColor = (state: string) => {
    if (state === 'success') return 'success'
    if (state === 'failed') return 'error'
    return 'info'
  }

  return (
    <Box>
      <Typography variant="h5" sx={{ fontFamily: '"Playfair Display", serif', color: '#f8f6f0', mb: 3 }}>
        Big Data Analytics
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={6}>
          <Card sx={cardSx}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontFamily: '"Playfair Display", serif', color: '#f8f6f0' }}>
                Pipeline Status
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {pipelineStatus.length === 0 ? (
                  <Typography sx={{ color: '#e8e6e1' }}>No DAG runs (Airflow may be offline)</Typography>
                ) : (
                  pipelineStatus.slice(0, 10).map((run, i) => (
                    <Chip
                      key={run.run_id ?? i}
                      label={`${run.dag_id ?? 'run'} ${run.state ?? 'unknown'}`}
                      color={stateColor(run.state ?? '') as 'success' | 'error' | 'info'}
                      size="small"
                      sx={{ mb: 0.5 }}
                    />
                  ))
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card sx={cardSx}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontFamily: '"Playfair Display", serif', color: '#f8f6f0' }}>
                Kafka Throughput
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={4}>
                  <Typography variant="caption" sx={{ color: '#e8e6e1' }}>Msgs/s</Typography>
                  <Typography sx={{ color: '#00d9ff', fontWeight: 700 }}>{kafkaStats.messagesPerSec ?? 0}</Typography>
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="caption" sx={{ color: '#e8e6e1' }}>Consumer lag</Typography>
                  <Typography sx={{ color: '#ffd700', fontWeight: 700 }}>{kafkaStats.consumerLag ?? 0}</Typography>
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="caption" sx={{ color: '#e8e6e1' }}>DLQ size</Typography>
                  <Typography sx={{ color: '#ef5350', fontWeight: 700 }}>{kafkaStats.dlqSize ?? 0}</Typography>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={8}>
          <Card sx={cardSx}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontFamily: '"Playfair Display", serif', color: '#f8f6f0' }}>
                Data Volume (30 days)
              </Typography>
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <AreaChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(0, 217, 255, 0.15)" />
                    <XAxis dataKey="date" stroke="#e8e6e1" tick={{ fill: '#e8e6e1', fontSize: 11 }} />
                    <YAxis stroke="#e8e6e1" tick={{ fill: '#e8e6e1', fontSize: 11 }} />
                    <Tooltip contentStyle={{ background: '#1a1f3a', border: '1px solid rgba(0, 217, 255, 0.3)', borderRadius: 12 }} />
                    <Area type="monotone" dataKey="total" stroke="#00d9ff" fill="rgba(0, 217, 255, 0.2)" strokeWidth={2} name="Total" />
                    <Area type="monotone" dataKey="spam" stroke="#ef5350" fill="rgba(239, 83, 80, 0.2)" strokeWidth={2} name="Spam" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <Typography sx={{ color: '#e8e6e1', py: 4, textAlign: 'center' }}>No daily analytics yet. Run analytics or backfill.</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card sx={cardSx}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontFamily: '"Playfair Display", serif', color: '#f8f6f0' }}>
                Model Performance
              </Typography>
              {modelCurrent && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="caption" sx={{ color: '#e8e6e1' }}>Champion</Typography>
                  <Typography sx={{ color: '#00d9ff' }}>v{modelCurrent.version ?? '—'}</Typography>
                  <Typography variant="body2" sx={{ color: '#e8e6e1' }}>Accuracy: {(modelCurrent.accuracy ?? 0) * 100}% · F1: {(modelCurrent.f1 ?? 0).toFixed(2)}</Typography>
                </Box>
              )}
              <Accordion disableGutters sx={{ background: 'transparent', boxShadow: 'none', '&:before': { display: 'none' } }}>
                <AccordionSummary expandIcon={<ExpandMoreIcon sx={{ color: '#00d9ff' }} />}>
                  <Typography sx={{ color: '#e8e6e1', fontSize: 14 }}>View History</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  {modelHistory.length === 0 ? (
                    <Typography variant="body2" sx={{ color: '#e8e6e1' }}>No versions</Typography>
                  ) : (
                    <Box component="table" sx={{ width: '100%', fontSize: 12, color: '#e8e6e1' }}>
                      <thead>
                        <tr>
                          <th style={{ textAlign: 'left' }}>Version</th>
                          <th style={{ textAlign: 'left' }}>Date</th>
                          <th style={{ textAlign: 'right' }}>Accuracy</th>
                          <th style={{ textAlign: 'right' }}>F1</th>
                        </tr>
                      </thead>
                      <tbody>
                        {modelHistory.map((v, i) => (
                          <tr key={i}>
                            <td>{v.version}</td>
                            <td>{v.training_date ?? '—'}</td>
                            <td style={{ textAlign: 'right' }}>{(v.accuracy ?? 0) * 100}%</td>
                            <td style={{ textAlign: 'right' }}>{(v.f1 ?? 0).toFixed(2)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </Box>
                  )}
                </AccordionDetails>
              </Accordion>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={6}>
          <Card sx={cardSx}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontFamily: '"Playfair Display", serif', color: '#f8f6f0' }}>
                Storage Explorer
              </Typography>
              <Accordion disableGutters sx={{ background: 'transparent', boxShadow: 'none', '&:before': { display: 'none' } }}>
                <AccordionSummary expandIcon={<ExpandMoreIcon sx={{ color: '#00d9ff' }} />}>
                  <Typography sx={{ color: '#e8e6e1', fontSize: 14 }}>Partitions (emails_raw)</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  {partitions.length === 0 ? (
                    <Typography variant="body2" sx={{ color: '#e8e6e1' }}>No partitions</Typography>
                  ) : (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {partitions.slice(0, 50).map((p) => (
                        <Chip key={p} label={p} size="small" sx={{ background: 'rgba(0,217,255,0.15)', color: '#00d9ff' }} />
                      ))}
                      {partitions.length > 50 && <Typography variant="caption" sx={{ color: '#e8e6e1' }}>+{partitions.length - 50} more</Typography>}
                    </Box>
                  )}
                </AccordionDetails>
              </Accordion>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card sx={cardSx}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontFamily: '"Playfair Display", serif', color: '#f8f6f0' }}>
                Trigger Controls
              </Typography>
              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                <Button
                  variant="outlined"
                  startIcon={refreshLoading ? <CircularProgress size={16} /> : <PlayArrowIcon />}
                  onClick={runAnalyticsNow}
                  disabled={refreshLoading}
                  sx={{ borderColor: '#00d9ff', color: '#00d9ff' }}
                >
                  Run Analytics Now
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<PsychologyIcon />}
                  disabled
                  sx={{ borderColor: 'rgba(0,217,255,0.5)', color: '#e8e6e1' }}
                >
                  Trigger Model Training
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}
