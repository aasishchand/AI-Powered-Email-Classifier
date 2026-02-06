import React, { useEffect, useState } from 'react'
import { Grid, Card, CardContent, Typography, Box, Alert } from '@mui/material'
import { EmailStats } from '../components/Dashboard/EmailStats'
import { TopicDistribution } from '../components/Dashboard/TopicDistribution'
import { SpamTrends } from '../components/Dashboard/SpamTrends'
import { LoadingSpinner } from '../components/Common/LoadingSpinner'
import { useEmailData } from '../hooks/useEmailData'
import { useWebSocket } from '../hooks/useWebSocket'
import type { DashboardMetrics } from '../types/analytics.types'

export function DashboardPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { fetchDashboardMetrics } = useEmailData()
  const { data: realtimeData, isConnected } = useWebSocket('/api/v1/ws/dashboard')

  useEffect(() => {
    fetchDashboardMetrics().then(setMetrics).catch((e) => setError(e.message || 'Failed')).finally(() => setLoading(false))
  }, [fetchDashboardMetrics])

  useEffect(() => {
    if (!realtimeData || !metrics) return
    if (typeof realtimeData !== 'object' || (realtimeData as { type?: string }).type !== 'metrics_update') return
    const d = (realtimeData as { data?: { new_emails?: number; new_spam?: number } }).data
    if (d) setMetrics((prev) => prev ? { ...prev, total_emails: prev.total_emails + (d.new_emails || 0), spam_count: prev.spam_count + (d.new_spam || 0) } : null)
  }, [realtimeData])

  if (loading) return <LoadingSpinner />
  if (error) return <Alert severity="error">{error}</Alert>
  if (!metrics) return <Alert severity="warning">No data</Alert>

  return (
    <Box>
      {!isConnected && <Alert severity="warning" sx={{ mb: 2 }}>Real-time updates disconnected.</Alert>}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card><CardContent>
            <Typography color="textSecondary" variant="subtitle2">Total Emails Today</Typography>
            <Typography variant="h4" color="primary">{metrics.total_emails.toLocaleString()}</Typography>
            <Typography variant="caption">↑ {metrics.change_from_yesterday ?? 0}% from yesterday</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card><CardContent>
            <Typography color="textSecondary" variant="subtitle2">Spam Detected</Typography>
            <Typography variant="h4" color="error">{metrics.spam_percentage.toFixed(1)}%</Typography>
            <Typography variant="caption">{metrics.spam_count} blocked</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card><CardContent>
            <Typography color="textSecondary" variant="subtitle2">Avg Response Time</Typography>
            <Typography variant="h4">{metrics.avg_response_time.toFixed(1)}h</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card><CardContent>
            <Typography color="textSecondary" variant="subtitle2">Time Saved Today</Typography>
            <Typography variant="h4" color="success.main">{metrics.time_saved_hours.toFixed(1)}h</Typography>
          </CardContent></Card>
        </Grid>
      </Grid>
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}><EmailStats /></Grid>
        <Grid item xs={12} md={4}><TopicDistribution topics={metrics.top_topics} /></Grid>
        <Grid item xs={12} md={6}><SpamTrends /></Grid>
      </Grid>
    </Box>
  )
}
