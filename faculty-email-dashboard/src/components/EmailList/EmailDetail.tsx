import React from 'react'
import { Dialog, DialogTitle, DialogContent, Typography, Chip, Box } from '@mui/material'
import type { Email } from '../../types/email.types'

/** Strip HTML so email body always shows as readable text, not raw source. */
function toPlainText(html: string | null | undefined): string {
  if (html == null || html === '') return ''
  const text = String(html)
  if (!text.includes('<') || !text.includes('>')) return text
  return text
    .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

interface Props {
  email: Email | null
  open: boolean
  onClose: () => void
}

export function EmailDetail({ email, open, onClose }: Props) {
  if (!email) return null
  const body = toPlainText(email.body || email.body_preview) || 'No content'
  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>{email.subject}</DialogTitle>
      <DialogContent>
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" color="textSecondary">From: {email.sender}</Typography>
          <Typography variant="body2" color="textSecondary">Date: {new Date(email.timestamp).toLocaleString()}</Typography>
          <Box sx={{ mt: 1 }}>
            {email.mailbox_type && <Chip label={email.mailbox_type} size="small" sx={{ mr: 1 }} color={email.mailbox_type === 'personal' ? 'secondary' : 'primary'} />}
            <Chip label={email.spam_label === 'spam' ? 'SPAM' : 'HAM'} color={email.spam_label === 'spam' ? 'error' : 'success'} size="small" sx={{ mr: 1 }} />
            {email.topic ? <Chip label={email.topic} size="small" variant="outlined" /> : null}
          </Box>
        </Box>
        <Typography component="div" variant="body1" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{body}</Typography>
      </DialogContent>
    </Dialog>
  )
}
