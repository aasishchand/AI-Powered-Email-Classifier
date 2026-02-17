import React, { useEffect, useState } from 'react'
import { Card, CardContent, Typography, Grid, Box, Chip } from '@mui/material'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell, Legend } from 'recharts'
import { useEmailData } from '../hooks/useEmailData'
import { LoadingSpinner } from '../components/Common/LoadingSpinner'
import type { DashboardMetrics } from '../types/analytics.types'

const PIE_COLORS = ['#00d9ff', '#ffd700', '#00C49F', '#FF8042', '#8884D8', '#82ca9d', '#ffc658', '#8dd1e1']

export function AnalyticsPage() {
  const [trends, setTrends] = useState<{ date: string; total: number; spam: number; ham: number; urgent: number }[]>([])
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const { fetchEmailTrends, fetchDashboardMetrics } = useEmailData()

  useEffect(() => {
    Promise.all([
      fetchEmailTrends(30).then((data) => setTrends(Array.isArray(data) ? data : [])),
      fetchDashboardMetrics().then(setMetrics),
    ]).finally(() => setLoading(false))
  }, [fetchEmailTrends, fetchDashboardMetrics])

  if (loading) return <LoadingSpinner />

  const chartData = trends.map((t) => ({ ...t, date: typeof t.date === 'string' ? t.date.slice(5, 10) : t.date }))
  const totalInRange = trends.reduce((s, t) => s + t.total, 0)
  const spamInRange = trends.reduce((s, t) => s + t.spam, 0)
  const hamInRange = trends.reduce((s, t) => s + t.ham, 0)
  const urgentInRange = trends.reduce((s, t) => s + t.urgent, 0)

  const topicPie = (metrics?.top_topics || []).slice(0, 8).map((t, i) => ({
    name: t.name,
    value: t.count,
    color: PIE_COLORS[i % PIE_COLORS.length],
  }))

  const cardSx = {
    border: '1px solid rgba(0, 217, 255, 0.2)',
    borderRadius: 3,
    background: 'rgba(26, 31, 58, 0.5)',
    backdropFilter: 'blur(10px)',
  }
  const statNum = {
    fontFamily: '"Playfair Display", serif',
    fontSize: '1.75rem',
    fontWeight: 800,
    background: 'linear-gradient(135deg, #00d9ff, #ffd700)',
    backgroundClip: 'text',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
  }

  return (
    <Box>
      <Typography variant="h5" sx={{ fontFamily: '"Playfair Display", serif', color: '#f8f6f0', mb: 3 }}>
        Analytics
      </Typography>

      {/* Summary cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {[
          { label: 'Total Emails', value: metrics?.total_emails ?? totalInRange },
          { label: 'Spam Detected', value: metrics?.spam_count ?? spamInRange, color: '#ef5350' },
          { label: 'Ham (Good)', value: hamInRange },
          { label: 'Urgent', value: urgentInRange, color: '#ffd700' },
          { label: 'Avg Urgency', value: `${((metrics?.avg_urgency ?? 0) * 100).toFixed(0)}%` },
          { label: 'Avg Email Length', value: `${metrics?.avg_email_length ?? 0} chars` },
        ].map((s, i) => (
          <Grid item xs={6} sm={4} md={2} key={i}>
            <Card sx={{ ...cardSx, textAlign: 'center' }}>
              <CardContent sx={{ py: 2 }}>
                <Typography variant="caption" sx={{ color: '#e8e6e1', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{s.label}</Typography>
                <Typography sx={{ ...statNum, fontSize: '1.5rem', ...(s.color ? { background: 'none', WebkitTextFillColor: s.color } : {}) }}>
                  {typeof s.value === 'number' ? s.value.toLocaleString() : s.value}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Volume trends */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={8}>
          <Card sx={cardSx}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontFamily: '"Playfair Display", serif', color: '#f8f6f0' }}>Email Volume (30 Days)</Typography>
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={320}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(0, 217, 255, 0.15)" />
                    <XAxis dataKey="date" stroke="#e8e6e1" tick={{ fill: '#e8e6e1', fontSize: 11 }} />
                    <YAxis stroke="#e8e6e1" tick={{ fill: '#e8e6e1', fontSize: 11 }} />
                    <Tooltip contentStyle={{ background: '#1a1f3a', border: '1px solid rgba(0, 217, 255, 0.3)', borderRadius: 12 }} />
                    <Line type="monotone" dataKey="total" stroke="#00d9ff" strokeWidth={2} name="Total" dot={false} />
                    <Line type="monotone" dataKey="spam" stroke="#ef5350" strokeWidth={2} name="Spam" dot={false} />
                    <Line type="monotone" dataKey="ham" stroke="#2e7d32" strokeWidth={2} name="Ham" dot={false} />
                    <Line type="monotone" dataKey="urgent" stroke="#ffd700" strokeWidth={2} name="Urgent" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <Typography sx={{ color: '#e8e6e1', py: 4, textAlign: 'center' }}>No email data yet. Sync your inbox first.</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Topic pie */}
        <Grid item xs={12} md={4}>
          <Card sx={cardSx}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontFamily: '"Playfair Display", serif', color: '#f8f6f0' }}>Topic Distribution</Typography>
              {topicPie.length > 0 ? (
                <ResponsiveContainer width="100%" height={320}>
                  <PieChart>
                    <Pie data={topicPie} cx="50%" cy="45%" innerRadius={50} outerRadius={75} paddingAngle={3} dataKey="value">
                      {topicPie.map((entry, idx) => (
                        <Cell key={idx} fill={entry.color} stroke="rgba(10,14,39,0.4)" strokeWidth={1} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value: number) => {
                        const total = topicPie.reduce((s, d) => s + d.value, 0)
                        return [`${total ? ((value / total) * 100).toFixed(1) : 0}%`]
                      }}
                      contentStyle={{ background: '#1a1f3a', border: '1px solid rgba(0,217,255,0.3)', borderRadius: 12 }}
                    />
                    <Legend layout="horizontal" align="center" verticalAlign="bottom" wrapperStyle={{ fontSize: 10, color: '#e8e6e1' }} iconType="circle" iconSize={6} formatter={(v) => <span style={{ color: '#e8e6e1' }}>{v}</span>} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <Typography sx={{ color: '#e8e6e1', py: 4, textAlign: 'center' }}>No topics yet.</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Spam vs Ham bar chart */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card sx={cardSx}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontFamily: '"Playfair Display", serif', color: '#f8f6f0' }}>Spam vs Ham (30 Days)</Typography>
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,217,255,0.15)" />
                    <XAxis dataKey="date" stroke="#e8e6e1" tick={{ fill: '#e8e6e1', fontSize: 11 }} />
                    <YAxis stroke="#e8e6e1" tick={{ fill: '#e8e6e1', fontSize: 11 }} />
                    <Tooltip contentStyle={{ background: '#1a1f3a', border: '1px solid rgba(0,217,255,0.3)', borderRadius: 12 }} />
                    <Bar dataKey="spam" fill="#ef5350" name="Spam" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="ham" fill="#00d9ff" name="Ham" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <Typography sx={{ color: '#e8e6e1', py: 4, textAlign: 'center' }}>No data yet.</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Topic breakdown list */}
        <Grid item xs={12} md={6}>
          <Card sx={cardSx}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontFamily: '"Playfair Display", serif', color: '#f8f6f0' }}>Top Topics Breakdown</Typography>
              {(metrics?.top_topics || []).length > 0 ? (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, mt: 1 }}>
                  {(metrics?.top_topics || []).map((t, i) => {
                    const maxCount = metrics?.top_topics?.[0]?.count || 1
                    const pct = Math.round((t.count / maxCount) * 100)
                    return (
                      <Box key={i}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                          <Typography variant="body2" sx={{ color: '#e8e6e1', fontSize: 13 }}>{t.name}</Typography>
                          <Chip label={t.count} size="small" sx={{ height: 20, fontSize: 11, background: 'rgba(0,217,255,0.15)', color: '#00d9ff' }} />
                        </Box>
                        <Box sx={{ height: 6, borderRadius: 3, background: 'rgba(255,255,255,0.08)' }}>
                          <Box sx={{ height: '100%', borderRadius: 3, width: `${pct}%`, background: `linear-gradient(90deg, ${PIE_COLORS[i % PIE_COLORS.length]}, ${PIE_COLORS[(i + 1) % PIE_COLORS.length]})` }} />
                        </Box>
                      </Box>
                    )
                  })}
                </Box>
              ) : (
                <Typography sx={{ color: '#e8e6e1', py: 4, textAlign: 'center' }}>No topics yet.</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}
