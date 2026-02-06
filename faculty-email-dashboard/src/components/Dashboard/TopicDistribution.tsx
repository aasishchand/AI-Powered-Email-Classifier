import React from 'react'
import { Card, CardContent, Typography } from '@mui/material'
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'
import type { TopicInfo } from '../../types/analytics.types'

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82ca9d', '#ffc658', '#ff7c7c', '#8dd1e1', '#d084d0']

interface Props {
  topics: TopicInfo[]
}

export function TopicDistribution({ topics }: Props) {
  const chartData = topics.slice(0, 10).map((t, i) => ({ name: t.name, value: t.count, category: t.category, color: COLORS[i % COLORS.length] }))

  return (
    <Card elevation={2}>
      <CardContent>
        <Typography variant="h6" gutterBottom>Email Topics Distribution</Typography>
        <ResponsiveContainer width="100%" height={350}>
          <PieChart>
            <Pie data={chartData} cx="50%" cy="50%" labelLine={false} label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`} outerRadius={100} fill="#8884d8" dataKey="value">
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
