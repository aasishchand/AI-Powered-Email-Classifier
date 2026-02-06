import { createSlice } from '@reduxjs/toolkit'

interface UserState {
  email: string | null
  fullName: string | null
  token: string | null
}

const initialState: UserState = {
  email: localStorage.getItem('user_email'),
  fullName: localStorage.getItem('user_full_name'),
  token: localStorage.getItem('access_token'),
}

const userSlice = createSlice({
  name: 'user',
  initialState,
  reducers: {
    setUser(state, action) {
      state.email = action.payload.email
      state.fullName = action.payload.fullName ?? null
      state.token = action.payload.token
      if (action.payload.token) localStorage.setItem('access_token', action.payload.token)
      if (action.payload.email) localStorage.setItem('user_email', action.payload.email)
      if (action.payload.fullName) localStorage.setItem('user_full_name', action.payload.fullName)
    },
    logout(state) {
      state.email = null
      state.fullName = null
      state.token = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('user_email')
      localStorage.removeItem('user_full_name')
    },
  },
})

export const { setUser, logout } = userSlice.actions
export default userSlice.reducer
