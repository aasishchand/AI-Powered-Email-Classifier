import React, { useEffect, useState } from 'react'
import { Card, CardContent, Typography } from '@mui/material'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { useEmailData } from '../hooks/useEmailData'
import { LoadingSpinner } from '../components/Common/LoadingSpinner'

export function AnalyticsPage() {
  const [trends, setTrends] = useState<{ date: string; total: number; spam: number; ham: number; urgent: number }[]>([])
  const [loading, setLoading] = useState(true)
  const { fetchEmailTrends } = useEmailData()

  useEffect(() => {
    fetchEmailTrends(30)
      .then((data) => setTrends(Array.isArray(data) ? data : []))
      .finally(() => setLoading(false))
  }, [fetchEmailTrends])

  if (loading) return <LoadingSpinner />
  const chartData = trends.map((t) => ({ ...t, date: typeof t.date === 'string' ? t.date.slice(0, 10) : t.date }))

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>Email Volume Trends (30 days)</Typography>
        <ResponsiveContainer width="100%" height={350}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="total" stroke="#1976d2" name="Total" />
            <Line type="monotone" dataKey="spam" stroke="#d32f2f" name="Spam" />
            <Line type="monotone" dataKey="ham" stroke="#2e7d32" name="Ham" />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
