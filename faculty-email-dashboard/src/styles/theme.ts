import { createTheme } from '@mui/material/styles'

const midnight = '#0a0e27'
const deepBlue = '#1a1f3a'
const electric = '#00d9ff'
const gold = '#ffd700'
const cream = '#f8f6f0'
const silver = '#e8e6e1'

export const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: electric },
    secondary: { main: gold },
    success: { main: '#2e7d32' },
    error: { main: '#ef5350' },
    warning: { main: '#ffb74d' },
    background: {
      default: midnight,
      paper: deepBlue,
    },
    text: {
      primary: cream,
      secondary: silver,
    },
  },
  typography: {
    fontFamily: '"DM Sans", "Inter", "Roboto", sans-serif',
    h1: { fontFamily: '"Playfair Display", serif', fontWeight: 800 },
    h2: { fontFamily: '"Playfair Display", serif', fontWeight: 700 },
    h3: { fontFamily: '"Playfair Display", serif', fontWeight: 600 },
    h4: { fontFamily: '"Playfair Display", serif', fontWeight: 600 },
    h5: { fontFamily: '"Playfair Display", serif', fontWeight: 600 },
    h6: { fontFamily: '"Playfair Display", serif', fontWeight: 600 },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: { backgroundColor: midnight },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          background: 'rgba(26, 31, 58, 0.5)',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(0, 217, 255, 0.2)',
          borderRadius: 16,
          '&:hover': {
            borderColor: electric,
            boxShadow: '0 20px 40px rgba(0, 217, 255, 0.15)',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          background: 'rgba(26, 31, 58, 0.6)',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(0, 217, 255, 0.2)',
          borderRadius: 16,
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        contained: {
          background: `linear-gradient(135deg, ${electric} 0%, #0099cc 100%)`,
          color: midnight,
          fontWeight: 700,
          borderRadius: 50,
          '&:hover': {
            background: `linear-gradient(135deg, ${electric} 0%, #0099cc 100%)`,
            boxShadow: '0 10px 30px rgba(0, 217, 255, 0.35)',
          },
        },
        outlined: {
          borderColor: silver,
          color: cream,
          borderRadius: 50,
          '&:hover': {
            borderColor: electric,
            color: electric,
            background: 'rgba(255, 255, 255, 0.05)',
          },
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 12,
            '& fieldset': { borderColor: 'rgba(0, 217, 255, 0.3)' },
            '&:hover fieldset': { borderColor: electric },
            '&.Mui-focused fieldset': { borderColor: electric },
          },
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          background: 'rgba(10, 14, 39, 0.85)',
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid rgba(0, 217, 255, 0.2)',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          background: 'rgba(26, 31, 58, 0.6)',
          backdropFilter: 'blur(10px)',
          borderRight: '1px solid rgba(0, 217, 255, 0.2)',
        },
      },
    },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          '&.active': {
            background: 'rgba(0, 217, 255, 0.15)',
            borderLeft: `3px solid ${electric}`,
          },
          '&:hover': {
            background: 'rgba(0, 217, 255, 0.08)',
          },
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          border: '1px solid rgba(0, 217, 255, 0.2)',
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          background: deepBlue,
          border: '1px solid rgba(0, 217, 255, 0.2)',
          borderRadius: 20,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          fontWeight: 500,
        },
      },
    },
  },
})

export const dashboardColors = { midnight, deepBlue, electric, gold, cream, silver }
