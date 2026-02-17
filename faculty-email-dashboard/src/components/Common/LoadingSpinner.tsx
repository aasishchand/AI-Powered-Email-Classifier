import { Box, CircularProgress } from '@mui/material'

export function LoadingSpinner() {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
      <CircularProgress sx={{ color: '#00d9ff' }} />
    </Box>
  )
}
