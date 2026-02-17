import { Outlet, useLocation } from 'react-router-dom'
import { Box } from '@mui/material'
import { AppBackground } from './AppBackground'
import { Header } from './Header'

export function Layout() {
  const location = useLocation()
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', color: '#f8f6f0' }}>
      <AppBackground />
      <Header />
      <Box component="main" sx={{ flexGrow: 1, p: 3, pt: 10, position: 'relative', zIndex: 0 }}>
        <Outlet key={location.pathname} />
      </Box>
    </Box>
  )
}
