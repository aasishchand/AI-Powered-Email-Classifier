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
    <Card elevation={2}>
      <CardContent>
        <Typography variant="h6" gutterBottom>Email Volume (14 Days)</Typography>
        <ResponsiveContainer width="100%" height={350}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="total" stroke="#1976d2" name="Total" />
            <Line type="monotone" dataKey="spam" stroke="#d32f2f" name="Spam" />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
