import { useQuery } from '@tanstack/react-query'
import { Alert, Box, Button, Chip, LinearProgress, Paper, Stack, Typography } from '@mui/material'
import School from '@mui/icons-material/SchoolOutlined'
import client from '@/api/client'
import { useAuthStore } from '@/store/authStore'

interface CatalogItem {
  id: string
  name: string
  code?: string
}

interface CatalogGroup extends CatalogItem {
  courses?: CatalogItem[]
  subjects?: CatalogItem[]
  sections?: CatalogItem[]
}

export default function StaffAcademicOverview() {
  const user = useAuthStore((state) => state.user)
  const isSchool = user?.institutions.some((institution) =>
    institution.tenant_id === user.current_tenant_id && institution.institution_type === 'SCHOOL'
  )
  const groups = isSchool ? ['sections'] as const : ['courses', 'subjects'] as const
  const catalog = useQuery({
    queryKey: ['staff-academic-overview', user?.id, user?.current_tenant_id, user?.current_role],
    queryFn: async () => (await client.get<{ data: CatalogGroup[] }>('/academics/staff-overview')).data.data,
  })

  return (
    <Stack spacing={2.5}>
      <Stack direction="row" alignItems="center" spacing={1.5}>
        <School color="primary" />
        <Box>
          <Typography variant="h4" component="h1">Academic Overview</Typography>
          <Typography color="text.secondary">
            {isSchool ? 'Classes and sections across your school.' : user?.current_role === 'HOD' ? 'Courses and subjects in your assigned departments.' : 'Departments, courses, and subjects across your institution.'}
          </Typography>
        </Box>
      </Stack>
      {catalog.isPending && <LinearProgress aria-label="Loading academic overview" />}
      {catalog.isError && <Alert severity="error" action={<Button onClick={() => void catalog.refetch()}>Retry</Button>}>Unable to load the academic overview.</Alert>}
      {catalog.data?.length === 0 && <Paper variant="outlined" sx={{ p: 4, textAlign: 'center' }}><Typography color="text.secondary">No {isSchool ? 'classes' : 'departments'} are available in your scope.</Typography></Paper>}
      {catalog.data?.map((department) => (
        <Paper variant="outlined" key={department.id} sx={{ p: { xs: 2, md: 2.5 } }}>
          <Stack direction="row" alignItems="center" gap={1} mb={2}>
            <Typography variant="h5" component="h2">{department.name}</Typography>
            <Chip size="small" label={department.code} variant="outlined" />
          </Stack>
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2 }}>
            {groups.map((key) => (
              <Box key={key} sx={{ bgcolor: 'action.hover', borderRadius: 2, p: 1.5 }}>
                <Typography variant="subtitle2" sx={{ textTransform: 'capitalize', mb: 1 }}>{key}</Typography>
                <Stack component="ul" spacing={0.75} sx={{ listStyle: 'none', p: 0, m: 0 }}>
                  {department[key]?.map((item) => (
                    <Stack component="li" key={item.id} direction="row" gap={1} justifyContent="space-between">
                      <Typography>{item.name}</Typography>
                      <Typography variant="caption" color="text.secondary">{item.code}</Typography>
                    </Stack>
                  ))}
                  {!department[key]?.length && <Typography component="li" color="text.secondary">No {key} recorded.</Typography>}
                </Stack>
              </Box>
            ))}
          </Box>
        </Paper>
      ))}
    </Stack>
  )
}
