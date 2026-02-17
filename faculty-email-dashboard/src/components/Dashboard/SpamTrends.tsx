import React, { useEffect, useState } from 'react'
import { Card, CardContent, Typography } from '@mui/material'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { useEmailData } from '../../hooks/useEmailData'

export function SpamTrends() {
  const [trends, setTrends] = useState<Record<string, number>[]>([])
  const { fetchEmailTrends } = useEmailData()
  useEffect(() => {
    fetchEmailTrends(14).then((d) => setTrends(Array.isArray(d) ? d : []))
  }, [fetchEmailTrends])
  const data = trends.map((t) => ({ date: (t as { date?: string }).date?.slice(0, 10) || '', spam: (t as { spam?: number }).spam ?? 0, ham: (t as { ham?: number }).ham ?? 0 }))
  return (
    <Card sx={{ border: '1px solid rgba(0, 217, 255, 0.2)', borderRadius: 3 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom sx={{ fontFamily: '"Playfair Display", serif', color: '#f8f6f0' }}>
          Spam vs Ham (14 Days)
        </Typography>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(0, 217, 255, 0.15)" />
            <XAxis dataKey="date" stroke="#e8e6e1" tick={{ fill: '#e8e6e1', fontSize: 12 }} />
            <YAxis stroke="#e8e6e1" tick={{ fill: '#e8e6e1', fontSize: 12 }} />
            <Tooltip contentStyle={{ background: '#1a1f3a', border: '1px solid rgba(0, 217, 255, 0.3)', borderRadius: 12 }} />
            <Bar dataKey="spam" fill="#ef5350" name="Spam" radius={[4, 4, 0, 0]} />
            <Bar dataKey="ham" fill="#00d9ff" name="Ham" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
