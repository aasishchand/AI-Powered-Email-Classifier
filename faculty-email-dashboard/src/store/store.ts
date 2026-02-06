import { configureStore } from '@reduxjs/toolkit'
import userReducer from './slices/userSlice'
import emailReducer from './slices/emailSlice'

export const store = configureStore({
  reducer: {
    user: userReducer,
    email: emailReducer,
  },
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
