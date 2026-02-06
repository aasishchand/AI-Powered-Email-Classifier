import { AppBar, Toolbar, Typography, Button, Box } from '@mui/material'
import { useAuth } from '../../hooks/useAuth'
import { logout } from '../../store/slices/userSlice'
import { useDispatch, useSelector } from 'react-redux'
import { useNavigate } from 'react-router-dom'
import type { RootState } from '../../store/store'

export function Header() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const email = useSelector((s: RootState) => s.user.email)

  const handleLogout = () => {
    dispatch(logout())
    navigate('/login')
  }

  return (
    <AppBar position="fixed" sx={{ zIndex: (t) => t.zIndex.drawer + 1 }}>
      <Toolbar>
        <Typography variant="h6" sx={{ flexGrow: 1 }}>
          Faculty & Personal Email Classification
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="body2">{email}</Typography>
          <Button color="inherit" onClick={handleLogout}>
            Logout
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  )
}
