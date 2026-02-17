import { useState, useCallback } from 'react'
import { api } from '../services/api'
import type { EmailFilters } from '../types/email.types'
import type { DashboardMetrics } from '../types/analytics.types'

export function useEmailData() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchDashboardMetrics = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const r = await api.get<DashboardMetrics>('/dashboard/metrics')
      return r.data
    } catch (e) {
      setError('Failed to fetch metrics')
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchEmails = useCallback(async (filters: EmailFilters = {}, page = 1, pageSize = 50) => {
    setLoading(true)
    setError(null)
    try {
      const r = await api.get('/emails/', { params: { ...filters, page, page_size: pageSize } })
      return r.data
    } catch (e) {
      setError('Failed to fetch emails')
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchEmailById = useCallback(async (messageId: string) => {
    setLoading(true)
    setError(null)
    try {
      const r = await api.get(`/emails/${encodeURIComponent(messageId)}`)
      return r.data
    } catch (e) {
      setError('Failed to load email')
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  const reclassifyEmail = useCallback(async (messageId: string, newLabel: string) => {
    setLoading(true)
    setError(null)
    try {
      await api.post(`/emails/${encodeURIComponent(messageId)}/reclassify`, { label: newLabel })
    } catch (e) {
      setError('Failed to reclassify')
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchEmailTrends = useCallback(async (days = 30) => {
    setLoading(true)
    setError(null)
    try {
      const r = await api.get('/dashboard/trends', { params: { days } })
      return r.data
    } catch (e) {
      setError('Failed to fetch trends')
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  return { loading, error, fetchDashboardMetrics, fetchEmails, reclassifyEmail, fetchEmailTrends }
}
