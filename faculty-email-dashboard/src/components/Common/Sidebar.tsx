import { NavLink } from 'react-router-dom'
import { List, ListItemButton, ListItemIcon, ListItemText, Drawer, Toolbar, Box } from '@mui/material'
import DashboardIcon from '@mui/icons-material/Dashboard'
import MailIcon from '@mui/icons-material/Mail'
import BarChartIcon from '@mui/icons-material/BarChart'
import SettingsIcon from '@mui/icons-material/Settings'

const drawerWidth = 240

const nav = [
  { to: '/dashboard', label: 'Dashboard', icon: <DashboardIcon /> },
  { to: '/emails', label: 'Emails', icon: <MailIcon /> },
  { to: '/analytics', label: 'Analytics', icon: <BarChartIcon /> },
  { to: '/settings', label: 'Settings', icon: <SettingsIcon /> },
]

export function Sidebar() {
  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: drawerWidth,
          boxSizing: 'border-box',
          top: 64,
          height: 'calc(100% - 64px)',
          background: 'rgba(26, 31, 58, 0.5)',
          backdropFilter: 'blur(10px)',
          borderRight: '1px solid rgba(0, 217, 255, 0.2)',
        },
      }}
    >
      <Toolbar />
      <Box sx={{ px: 1.5, py: 2 }}>
        <List disablePadding>
          {nav.map(({ to, label, icon }) => (
            <ListItemButton
              key={to}
              component={NavLink}
              to={to}
              sx={{
                borderRadius: 2,
                mb: 0.5,
                color: '#e8e6e1',
                '&.active': {
                  background: 'rgba(0, 217, 255, 0.15)',
                  borderLeft: '3px solid #00d9ff',
                  color: '#00d9ff',
                  '& .MuiListItemIcon-root': { color: '#00d9ff' },
                },
                '&:hover': {
                  background: 'rgba(0, 217, 255, 0.08)',
                  color: '#00d9ff',
                  '& .MuiListItemIcon-root': { color: '#00d9ff' },
                },
              }}
            >
              <ListItemIcon sx={{ color: 'inherit', minWidth: 40 }}>{icon}</ListItemIcon>
              <ListItemText primary={label} primaryTypographyProps={{ fontWeight: 500 }} />
            </ListItemButton>
          ))}
        </List>
      </Box>
    </Drawer>
  )
}
