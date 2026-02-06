import { NavLink } from 'react-router-dom'
import { List, ListItemButton, ListItemIcon, ListItemText, Drawer, Toolbar } from '@mui/material'
import DashboardIcon from '@mui/icons-material/Dashboard'
import MailIcon from '@mui/icons-material/Mail'
import BarChartIcon from '@mui/icons-material/BarChart'
import SettingsIcon from '@mui/icons-material/Settings'

const drawerWidth = 220

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
        },
      }}
    >
      <Toolbar />
      <List>
        {nav.map(({ to, label, icon }) => (
          <ListItemButton key={to} component={NavLink} to={to} sx={{ '&.active': { bgcolor: 'action.selected' } }}>
            <ListItemIcon>{icon}</ListItemIcon>
            <ListItemText primary={label} />
          </ListItemButton>
        ))}
      </List>
    </Drawer>
  )
}
