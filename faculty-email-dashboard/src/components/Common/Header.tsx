import { AppBar, Toolbar, Typography, Button, Box, Link } from '@mui/material'
import { NavLink, useNavigate } from 'react-router-dom'
import { logout } from '../../store/slices/userSlice'
import { useDispatch, useSelector } from 'react-redux'
import type { RootState } from '../../store/store'

const navLinks = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/emails', label: 'Emails' },
  { to: '/analytics', label: 'Analytics' },
  { to: '/settings', label: 'Settings' },
]

export function Header() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const email = useSelector((s: RootState) => s.user.email)

  const handleLogout = () => {
    dispatch(logout())
    navigate('/login')
  }

  return (
    <AppBar
      position="fixed"
      elevation={0}
      sx={{
        zIndex: (t) => t.zIndex.drawer + 1,
        background: 'rgba(10, 14, 39, 0.9)',
        backdropFilter: 'blur(10px)',
        borderBottom: '1px solid rgba(0, 217, 255, 0.2)',
      }}
    >
      <Toolbar sx={{ justifyContent: 'space-between', px: { xs: 2, md: 4 }, minHeight: 64 }}>
        {/* Logo - gradient like reference "Demo Workspace" */}
        <Typography
          component={NavLink}
          to="/dashboard"
          variant="h6"
          sx={{
            fontFamily: '"Playfair Display", serif',
            fontWeight: 800,
            letterSpacing: '-0.02em',
            background: 'linear-gradient(135deg, #00d9ff 0%, #ffd700 100%)',
            backgroundClip: 'text',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            textDecoration: 'none',
            mr: 4,
          }}
        >
          Faculty & Personal Email
        </Typography>

        {/* Nav links - like Features, Analytics, Metrics, Contact in reference */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: { xs: 1.5, md: 3 } }}>
          {navLinks.map(({ to, label }) => (
            <Link
              key={to}
              component={NavLink}
              to={to}
              sx={{
                color: '#e8e6e1',
                textDecoration: 'none',
                fontWeight: 500,
                fontSize: '0.95rem',
                letterSpacing: '0.02em',
                position: 'relative',
                '&::after': {
                  content: '""',
                  position: 'absolute',
                  bottom: -5,
                  left: 0,
                  width: 0,
                  height: 2,
                  background: 'linear-gradient(90deg, #00d9ff, #ffd700)',
                  transition: 'width 0.3s ease',
                },
                '&:hover': { color: '#00d9ff' },
                '&:hover::after': { width: '100%' },
                '&.active': { color: '#00d9ff', '&::after': { width: '100%' } },
              }}
            >
              {label}
            </Link>
          ))}
        </Box>

        {/* Right: user email + Get Started-style CTA */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, ml: 2 }}>
          <Typography variant="body2" sx={{ color: '#e8e6e1', display: { xs: 'none', sm: 'block' } }}>
            {email}
          </Typography>
          <Button
            variant="contained"
            onClick={handleLogout}
            sx={{
              px: 2.5,
              py: 1,
              borderRadius: 50,
              fontWeight: 700,
              fontSize: '0.95rem',
              background: 'linear-gradient(135deg, #00d9ff 0%, #0099cc 100%)',
              color: '#0a0e27',
              '&:hover': {
                boxShadow: '0 10px 30px rgba(0, 217, 255, 0.35)',
                background: 'linear-gradient(135deg, #00d9ff 0%, #0099cc 100%)',
              },
            }}
          >
            Logout
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  )
}
