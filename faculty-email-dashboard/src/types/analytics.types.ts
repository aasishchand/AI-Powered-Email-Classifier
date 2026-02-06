export interface TopicInfo {
  name: string
  category: string
  count: number
}

export interface DashboardMetrics {
  total_emails: number
  spam_count: number
  spam_percentage: number
  avg_sentiment: number
  avg_urgency: number
  top_topics: TopicInfo[]
  time_saved_hours: number
  avg_response_time: number
  change_from_yesterday: number
  avg_email_length: number
}

export interface EmailTrend {
  date: string
  total: number
  spam: number
  ham: number
  urgent: number
}
