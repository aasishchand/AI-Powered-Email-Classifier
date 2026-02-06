import React from 'react'
import { Dialog, DialogTitle, DialogContent, Typography, Chip, Box } from '@mui/material'
import type { Email } from '../../types/email.types'

interface Props {
  email: Email | null
  open: boolean
  onClose: () => void
}

export function EmailDetail({ email, open, onClose }: Props) {
  if (!email) return null
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
        <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>{email.body || email.body_preview || 'No content'}</Typography>
      </DialogContent>
    </Dialog>
  )
}
