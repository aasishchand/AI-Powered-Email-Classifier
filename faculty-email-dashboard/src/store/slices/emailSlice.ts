import { createSlice } from '@reduxjs/toolkit'
import type { Email } from '../../types/email.types'

interface EmailState {
  list: Email[]
  total: number
  selectedMessageId: string | null
}

const initialState: EmailState = {
  list: [],
  total: 0,
  selectedMessageId: null,
}

const emailSlice = createSlice({
  name: 'email',
  initialState,
  reducers: {
    setEmails(state, action) {
      state.list = action.payload.emails
      state.total = action.payload.total
    },
    setSelectedEmail(state, action) {
      state.selectedMessageId = action.payload
    },
  },
})

export const { setEmails, setSelectedEmail } = emailSlice.actions
export default emailSlice.reducer
