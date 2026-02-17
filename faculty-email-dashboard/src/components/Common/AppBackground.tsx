import { Box } from '@mui/material'

const noiseSvg = "data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E"

export function AppBackground() {
  return (
    <>
      <Box
        sx={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          zIndex: -2,
          background: `
            radial-gradient(ellipse 80% 50% at 50% -20%, rgba(0, 217, 255, 0.12), transparent),
            radial-gradient(ellipse 60% 50% at 80% 50%, rgba(255, 215, 0, 0.06), transparent),
            radial-gradient(circle at 20% 80%, rgba(0, 217, 255, 0.08), transparent),
            #0a0e27
          `,
        }}
      />
      <Box
        sx={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          zIndex: -1,
          opacity: 0.03,
          backgroundImage: `url("${noiseSvg}")`,
          pointerEvents: 'none',
        }}
      />
    </>
  )
}
