import React from 'react'
import { Card, CardContent, Typography } from '@mui/material'
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'
import type { TopicInfo } from '../../types/analytics.types'

const COLORS = ['#00d9ff', '#ffd700', '#00C49F', '#FF8042', '#8884D8', '#82ca9d', '#ffc658', '#8dd1e1']

interface Props {
  topics: TopicInfo[]
}

export function TopicDistribution({ topics }: Props) {
  const chartData = topics.slice(0, 8).map((t, i) => ({ name: t.name, value: t.count, color: COLORS[i % COLORS.length] }))

  return (
    <Card sx={{ border: '1px solid rgba(0, 217, 255, 0.2)', borderRadius: 3 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom sx={{ fontFamily: '"Playfair Display", serif', color: '#f8f6f0' }}>
          Email Topics Distribution
        </Typography>
        <ResponsiveContainer width="100%" height={320}>
          <PieChart margin={{ top: 24, right: 24, bottom: 48, left: 24 }}>
            <Pie
              data={chartData}
              cx="50%"
              cy="45%"
              innerRadius={52}
              outerRadius={78}
              paddingAngle={3}
              dataKey="value"
              isAnimationActive={true}
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} stroke="rgba(10, 14, 39, 0.4)" strokeWidth={1} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number, name: string, props: { payload: { value: number } }) => {
                const total = chartData.reduce((s, d) => s + d.value, 0)
                const pct = total ? ((props.payload.value / total) * 100).toFixed(1) : '0'
                return [`${pct}%`, name]
              }}
              contentStyle={{ background: '#1a1f3a', border: '1px solid rgba(0, 217, 255, 0.3)', borderRadius: 12 }}
            />
            <Legend
              layout="horizontal"
              align="center"
              verticalAlign="bottom"
              wrapperStyle={{ color: '#e8e6e1', fontSize: 11 }}
              iconType="circle"
              iconSize={6}
              formatter={(value) => <span style={{ color: '#e8e6e1' }}>{value}</span>}
            />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
