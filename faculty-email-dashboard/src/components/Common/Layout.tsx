import { Outlet } from 'react-router-dom'
import { Box } from '@mui/material'
import { Header } from './Header'
import { Sidebar } from './Sidebar'

export function Layout() {
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <Header />
      <Sidebar />
      <Box component="main" sx={{ flexGrow: 1, p: 3, mt: 8, ml: 8 }}>
        <Outlet />
      </Box>
    </Box>
  )
}
