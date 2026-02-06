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
    <Card elevation={2}>
      <CardContent>
        <Typography variant="h6" gutterBottom>Spam vs Ham (14 Days)</Typography>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="spam" fill="#d32f2f" name="Spam" />
            <Bar dataKey="ham" fill="#2e7d32" name="Ham" />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
