import React, { useEffect, useState } from 'react'
import { Card, CardContent, Typography } from '@mui/material'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { useEmailData } from '../../hooks/useEmailData'

export function EmailStats() {
  const [trends, setTrends] = useState<{ date: string; total: number; spam: number }[]>([])
  const { fetchEmailTrends } = useEmailData()
  useEffect(() => {
    fetchEmailTrends(14).then((d) => setTrends(Array.isArray(d) ? d : []))
  }, [fetchEmailTrends])
  const data = trends.map((t) => ({ ...t, date: typeof t.date === 'string' ? t.date.slice(0, 10) : t.date }))
  return (
    <Card sx={{ border: '1px solid rgba(0, 217, 255, 0.2)', borderRadius: 3 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom sx={{ fontFamily: '"Playfair Display", serif', color: '#f8f6f0' }}>Email Volume (14 Days)</Typography>
        <ResponsiveContainer width="100%" height={350}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(0, 217, 255, 0.15)" />
            <XAxis dataKey="date" stroke="#e8e6e1" tick={{ fill: '#e8e6e1', fontSize: 12 }} />
            <YAxis stroke="#e8e6e1" tick={{ fill: '#e8e6e1', fontSize: 12 }} />
            <Tooltip contentStyle={{ background: '#1a1f3a', border: '1px solid rgba(0, 217, 255, 0.3)', borderRadius: 12 }} />
            <Line type="monotone" dataKey="total" stroke="#00d9ff" strokeWidth={2} name="Total" dot={{ fill: '#00d9ff' }} />
            <Line type="monotone" dataKey="spam" stroke="#ef5350" strokeWidth={2} name="Spam" dot={{ fill: '#ef5350' }} />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
