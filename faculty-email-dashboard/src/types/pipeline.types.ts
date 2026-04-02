export interface PipelineEmail {
  email_id: string
  text: string
  predicted_label: string
  confidence: number | null
  timestamp: string | null
  feedback: string | null
  feedback_at: string | null
  /** mailbox = Gmail/saved inbox; synthetic = Python producer; demo = UI sample button */
  pipeline_source?: string | null
}

export interface PipelineEmailsResponse {
  items: PipelineEmail[]
  count: number
}
