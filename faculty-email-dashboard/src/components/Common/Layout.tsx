import { Outlet, useLocation } from 'react-router-dom'
import { Box } from '@mui/material'
import { AppBackground } from './AppBackground'
import { Header } from './Header'
import { SIDEBAR_DRAWER_WIDTH, Sidebar } from './Sidebar'

export function Layout() {
  const location = useLocation()
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', color: '#f8f6f0' }}>
      <AppBackground />
      <Header />
      <Box sx={{ display: 'flex', flexGrow: 1, minHeight: 0, position: 'relative' }}>
        <Sidebar />
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            p: 3,
            pt: 10,
            ml: `${SIDEBAR_DRAWER_WIDTH}px`,
            position: 'relative',
            zIndex: 0,
            width: `calc(100% - ${SIDEBAR_DRAWER_WIDTH}px)`,
            maxWidth: `calc(100% - ${SIDEBAR_DRAWER_WIDTH}px)`,
            boxSizing: 'border-box',
          }}
        >
          <Outlet key={location.pathname} />
        </Box>
      </Box>
    </Box>
  )
}
