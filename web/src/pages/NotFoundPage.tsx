import { Box, Typography, Button } from '@mui/material'
import { useNavigate } from 'react-router-dom'

export default function NotFoundPage() {
  const navigate = useNavigate()
  return (
    <Box
      display="flex"
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      minHeight="100vh"
      gap={2}
      textAlign="center"
      px={3}
    >
      <Typography variant="h1" fontWeight={800} sx={{ fontSize: '6rem', color: 'primary.main' }}>
        404
      </Typography>
      <Typography variant="h5" fontWeight={600}>Page not found</Typography>
      <Typography variant="body2" color="text.secondary" maxWidth={400}>
        The page you are looking for does not exist or has been moved.
      </Typography>
      <Button variant="contained" onClick={() => navigate('/')} sx={{ mt: 2 }}>
        Go Home
      </Button>
    </Box>
  )
}
