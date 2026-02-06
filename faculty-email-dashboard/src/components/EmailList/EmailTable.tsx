import React, { useState, useEffect } from 'react'
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TablePagination, Paper, Chip, IconButton, Checkbox, Tooltip, Box, ToggleButtonGroup, ToggleButton } from '@mui/material'
import { Flag as FlagIcon, CheckCircle as CheckCircleIcon, Warning as WarningIcon, Work as WorkIcon, Person as PersonIcon, Inbox as InboxIcon } from '@mui/icons-material'
import { useEmailData } from '../../hooks/useEmailData'
import type { Email, EmailFilters } from '../../types/email.types'
import { EmailDetail } from './EmailDetail'
import { LoadingSpinner } from '../Common/LoadingSpinner'

type MailboxFilter = 'all' | 'faculty' | 'personal'

export function EmailTable() {
  const [emails, setEmails] = useState<Email[]>([])
  const [selectedEmails, setSelectedEmails] = useState<Set<string>>(new Set())
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(25)
  const [totalCount, setTotalCount] = useState(0)
  const [selectedEmail, setSelectedEmail] = useState<Email | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [mailboxFilter, setMailboxFilter] = useState<MailboxFilter>('all')
  const { fetchEmails, reclassifyEmail, loading } = useEmailData()

  const loadEmails = async () => {
    try {
      const filters: EmailFilters = mailboxFilter !== 'all' ? { mailbox_type: mailboxFilter } : {}
      const result = await fetchEmails(filters, page + 1, rowsPerPage)
      setEmails(result.emails || [])
      setTotalCount(result.total || 0)
    } catch (e) {
      console.error(e)
    }
  }

  useEffect(() => {
    setPage(0)
  }, [mailboxFilter])

  useEffect(() => {
    loadEmails()
  }, [page, rowsPerPage, mailboxFilter])

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) setSelectedEmails(new Set(emails.map((x) => x.message_id)))
    else setSelectedEmails(new Set())
  }

  const handleSelectOne = (id: string) => {
    const next = new Set(selectedEmails)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setSelectedEmails(next)
  }

  const handleReclassify = async (messageId: string, newLabel: string) => {
    try {
      await reclassifyEmail(messageId, newLabel)
      loadEmails()
    } catch (e) {
      console.error(e)
    }
  }

  const handleViewDetail = (email: Email) => {
    setSelectedEmail(email)
    setDetailOpen(true)
  }

  if (loading && emails.length === 0) return <LoadingSpinner />

  return (
    <Box>
      <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
        <span style={{ marginRight: 8 }}>Mailbox:</span>
        <ToggleButtonGroup
          value={mailboxFilter}
          exclusive
          onChange={(_, v: MailboxFilter | null) => v != null && setMailboxFilter(v)}
          size="small"
        >
          <ToggleButton value="all"><InboxIcon sx={{ mr: 0.5 }} /> All</ToggleButton>
          <ToggleButton value="faculty"><WorkIcon sx={{ mr: 0.5 }} /> Faculty</ToggleButton>
          <ToggleButton value="personal"><PersonIcon sx={{ mr: 0.5 }} /> Personal</ToggleButton>
        </ToggleButtonGroup>
      </Box>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox">
                <Checkbox indeterminate={selectedEmails.size > 0 && selectedEmails.size < emails.length} checked={emails.length > 0 && selectedEmails.size === emails.length} onChange={handleSelectAll} />
              </TableCell>
              <TableCell>Mailbox</TableCell>
              <TableCell>Sender</TableCell>
              <TableCell>Subject</TableCell>
              <TableCell>Topic</TableCell>
              <TableCell>Classification</TableCell>
              <TableCell>Urgency</TableCell>
              <TableCell>Date</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {emails.map((email) => (
              <TableRow key={email.message_id} hover onClick={() => handleViewDetail(email)} sx={{ cursor: 'pointer' }}>
                <TableCell padding="checkbox" onClick={(ev) => ev.stopPropagation()}>
                  <Checkbox checked={selectedEmails.has(email.message_id)} onChange={() => handleSelectOne(email.message_id)} />
                </TableCell>
                <TableCell>
                  <Chip label={email.mailbox_type || 'faculty'} size="small" variant="outlined" color={email.mailbox_type === 'personal' ? 'secondary' : 'primary'} />
                </TableCell>
                <TableCell>{email.sender}</TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {email.urgency_score > 0.7 ? <WarningIcon color="error" /> : email.urgency_score > 0.4 ? <FlagIcon color="warning" /> : null}
                    {email.subject}
                  </Box>
                </TableCell>
                <TableCell>{email.topic ? <Chip label={email.topic} size="small" variant="outlined" /> : null}</TableCell>
                <TableCell>{email.spam_label === 'spam' ? <Chip label="SPAM" color="error" size="small" /> : <Chip label="HAM" color="success" size="small" />}</TableCell>
                <TableCell><Chip label={`${(email.urgency_score * 100).toFixed(0)}%`} size="small" color={email.urgency_score > 0.7 ? 'error' : 'default'} /></TableCell>
                <TableCell>{new Date(email.timestamp).toLocaleDateString()}</TableCell>
                <TableCell onClick={(ev) => ev.stopPropagation()}>
                  {email.spam_label === 'spam' ? (
                    <Tooltip title="Mark as Not Spam"><IconButton size="small" onClick={() => handleReclassify(email.message_id, 'ham')}><CheckCircleIcon /></IconButton></Tooltip>
                  ) : (
                    <Tooltip title="Mark as Spam"><IconButton size="small" onClick={() => handleReclassify(email.message_id, 'spam')}><FlagIcon /></IconButton></Tooltip>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <TablePagination count={totalCount} page={page} onPageChange={(_, p) => setPage(p)} rowsPerPage={rowsPerPage} onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0) }} rowsPerPageOptions={[25, 50, 100]} component="div" />
      </TableContainer>
      <EmailDetail email={selectedEmail} open={detailOpen} onClose={() => setDetailOpen(false)} />
    </Box>
  )
}
