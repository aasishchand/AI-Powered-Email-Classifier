export interface Email {
  message_id: string
  sender: string
  sender_name?: string
  subject: string
  body?: string
  body_preview?: string
  timestamp: string
  spam_label: string
  spam_score: number
  topic?: string
  topic_confidence?: number
  urgency_score: number
  sentiment_score: number
  attachment_count: number
  cc_count: number
  mailbox_type?: 'faculty' | 'personal'
}

export interface EmailFilters {
  start_date?: string
  end_date?: string
  topic?: string
  spam_label?: string
  sender?: string
  search?: string
  mailbox_type?: 'faculty' | 'personal'
}
