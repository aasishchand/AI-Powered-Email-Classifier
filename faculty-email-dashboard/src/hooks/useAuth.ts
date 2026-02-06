import { useDispatch, useSelector } from 'react-redux'
import { useNavigate } from 'react-router-dom'
import type { RootState } from '../store/store'
import { logout } from '../store/slices/userSlice'

export function useAuth() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const token = useSelector((s: RootState) => s.user.token)
  const email = useSelector((s: RootState) => s.user.email)
  const fullName = useSelector((s: RootState) => s.user.fullName)

  function isAuthenticated() {
    return !!token
  }

  function doLogout() {
    dispatch(logout())
    navigate('/login')
  }

  return { token, email, fullName, isAuthenticated, logout: doLogout }
}
