import { useState } from 'react'
import {
  Alert,
  Box,
  Card,
  CardContent,
  Typography,
  Tabs,
  Tab,
  Grid,
  Chip,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Switch,
  FormControlLabel,
  CircularProgress,
  Paper,
  Divider,
} from '@mui/material'
import IntegrationInstructionsIcon from '@mui/icons-material/IntegrationInstructions'
import SettingsIcon from '@mui/icons-material/Settings'
import PaymentIcon from '@mui/icons-material/Payment'
import CloudQueueIcon from '@mui/icons-material/CloudQueue'
import EmailIcon from '@mui/icons-material/Email'
import WhatsAppIcon from '@mui/icons-material/WhatsApp'
import SmsIcon from '@mui/icons-material/Sms'
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { superAdminApi, PlatformIntegrationItem } from '@/api/superAdmin'
import { PageHeader } from '@/components/ui/PageHeader'

interface BrandingDraft {
  app_name?: string
  support_email?: string
  maintenance_mode?: boolean
}

export default function SettingsIntegrationsPage() {
  const queryClient = useQueryClient()
  const [tab, setTab] = useState(0)

  const [draft, setDraft] = useState<BrandingDraft>({})

  // Integration edit state
  const [editingIntegration, setEditingIntegration] = useState<PlatformIntegrationItem | null>(null)
  const [integrationEnabled, setIntegrationEnabled] = useState(false)
  const [integrationConfigJson, setIntegrationConfigJson] = useState('{}')
  const [integrationError, setIntegrationError] = useState('')

  const settings = useQuery({
    queryKey: ['superAdminSettings'],
    queryFn: superAdminApi.getSettings,
  })
  const savedBranding = settings.data?.find((setting) => setting.category === 'GENERAL' && setting.key === 'platform_branding')?.value
  const appName = draft.app_name ?? String(savedBranding?.app_name ?? 'EduSaaS CRM Platform')
  const supportEmail = draft.support_email ?? String(savedBranding?.support_email ?? 'support@edusaas.com')
  const maintenanceMode = draft.maintenance_mode ?? savedBranding?.maintenance_mode === true

  const { data: integrations, isLoading: integrationsLoading, isError: integrationsError } = useQuery({
    queryKey: ['superAdminIntegrations'],
    queryFn: superAdminApi.listIntegrations,
  })

  const updateIntegrationMutation = useMutation({
    mutationFn: ({ provider, is_enabled, config }: { provider: string; is_enabled: boolean; config: Record<string, unknown> }) =>
      superAdminApi.updateIntegration(provider, { is_enabled, config }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['superAdminIntegrations'] })
      setEditingIntegration(null)
    },
  })

  const updateSettingMutation = useMutation({
    mutationFn: (payload: { category: string; key: string; value: Record<string, unknown>; description?: string }) =>
      superAdminApi.updateSetting(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['superAdminSettings'] })
      setDraft({})
    },
  })

  const getProviderIcon = (provider: string) => {
    switch (provider) {
      case 'RAZORPAY':
        return <PaymentIcon sx={{ fontSize: 32, color: '#3b82f6' }} />
      case 'AWS_S3':
        return <CloudQueueIcon sx={{ fontSize: 32, color: '#f59e0b' }} />
      case 'RESEND':
        return <EmailIcon sx={{ fontSize: 32, color: '#10b981' }} />
      case 'META_WHATSAPP':
        return <WhatsAppIcon sx={{ fontSize: 32, color: '#22c55e' }} />
      case 'MSG91':
        return <SmsIcon sx={{ fontSize: 32, color: '#ec4899' }} />
      case 'FIREBASE_FCM':
        return <NotificationsActiveIcon sx={{ fontSize: 32, color: '#f97316' }} />
      default:
        return <IntegrationInstructionsIcon sx={{ fontSize: 32, color: 'primary.main' }} />
    }
  }

  const handleOpenEditIntegration = (item: PlatformIntegrationItem) => {
    setIntegrationError('')
    updateIntegrationMutation.reset()
    setEditingIntegration(item)
    setIntegrationEnabled(item.is_enabled)
    setIntegrationConfigJson(JSON.stringify(item.config, null, 2))
  }

  const handleSaveIntegration = () => {
    if (!editingIntegration) return
    setIntegrationError('')
    try {
      const parsedConfig = JSON.parse(integrationConfigJson)
      if (parsedConfig === null || typeof parsedConfig !== 'object' || Array.isArray(parsedConfig)) {
        setIntegrationError('Enter a JSON object for the provider configuration.')
        return
      }
      updateIntegrationMutation.mutate({
        provider: editingIntegration.provider,
        is_enabled: integrationEnabled,
        config: parsedConfig,
      })
    } catch {
      setIntegrationError('The provider configuration contains invalid JSON.')
    }
  }

  const handleSaveGeneralSettings = () => {
    updateSettingMutation.mutate({
      category: 'GENERAL',
      key: 'platform_branding',
      value: { app_name: appName, support_email: supportEmail, maintenance_mode: maintenanceMode },
      description: 'Platform name and customer support contact email',
    })
  }

  return (
    <Box>
      <Box mb={3}>
        <PageHeader title="Platform Settings" description="Manage platform details and provider configuration." icon={<SettingsIcon />} />
      </Box>

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={tab} onChange={(_, newTab) => setTab(newTab)}>
          <Tab icon={<SettingsIcon />} iconPosition="start" label="Global Settings" />
          <Tab icon={<IntegrationInstructionsIcon />} iconPosition="start" label="Third-Party Integrations" />
        </Tabs>
      </Box>

      {/* Tab 0: Global Platform Settings */}
      {tab === 0 && (
        <Card sx={{ maxWidth: 800 }}>
          <CardContent>
            <Typography variant="h6" fontWeight={600} mb={2}>
              General Platform Identity & Operations
            </Typography>

            {settings.isError && <Alert severity="error">Platform settings could not be loaded.</Alert>}
            {updateSettingMutation.isError && <Alert severity="error">Platform settings could not be saved.</Alert>}
            {updateSettingMutation.isSuccess && <Alert severity="success">Platform settings saved.</Alert>}
            <Box component="form" onSubmit={(event) => {
              event.preventDefault()
              handleSaveGeneralSettings()
            }} display="flex" flexDirection="column" gap={2.5}>
              <TextField
                label="SaaS Platform Name"
                size="small"
                value={appName}
                onChange={(event) => setDraft({ ...draft, app_name: event.target.value })}
                required
                disabled={settings.isLoading || updateSettingMutation.isPending}
                fullWidth
              />

              <TextField
                label="Default Support Email"
                size="small"
                value={supportEmail}
                onChange={(event) => setDraft({ ...draft, support_email: event.target.value })}
                type="email"
                required
                disabled={settings.isLoading || updateSettingMutation.isPending}
                fullWidth
              />

              <Paper variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={maintenanceMode}
                      onChange={(event) => setDraft({ ...draft, maintenance_mode: event.target.checked })}
                      disabled={settings.isLoading || updateSettingMutation.isPending}
                      color="warning"
                    />
                  }
                  label="Maintenance Mode"
                />
                <Typography variant="caption" color="text.secondary" display="block">
                  Records the platform maintenance preference.
                </Typography>
              </Paper>

              <Box display="flex" justifyContent="flex-end" mt={2}>
                <Button
                  variant="contained"
                  type="submit"
                  disabled={settings.isLoading || settings.isError || updateSettingMutation.isPending || !appName.trim()}
                >
                  {updateSettingMutation.isPending ? <CircularProgress size={20} /> : 'Save Settings'}
                </Button>
              </Box>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Tab 1: Integrations */}
      {tab === 1 && (
        <Box>
          {integrationsLoading ? (
            <Box display="flex" justifyContent="center" py={5}>
              <CircularProgress />
            </Box>
          ) : integrationsError ? (
            <Alert severity="error">Provider integrations could not be loaded.</Alert>
          ) : (
            <Grid container spacing={3}>
              {integrations?.map((item) => (
                <Grid item xs={12} sm={6} md={4} key={item.id}>
                  <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                    <CardContent sx={{ flex: 1 }}>
                      <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
                        {getProviderIcon(item.provider)}
                        <Chip
                          label={item.is_enabled ? 'ENABLED' : 'DISABLED'}
                          size="small"
                          color={item.is_enabled ? 'success' : 'default'}
                        />
                      </Box>

                      <Typography variant="h6" fontWeight={700}>
                        {item.name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" display="block" mb={2}>
                        Provider: <code>{item.provider}</code>
                      </Typography>

                      <Divider sx={{ my: 1.5 }} />

                      <Box display="flex" justifyContent="space-between" alignItems="center">
                        <Typography variant="caption" color="text.secondary">
                          Status: {item.status}
                        </Typography>
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => handleOpenEditIntegration(item)}
                        >
                          Configure
                        </Button>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          )}
        </Box>
      )}

      {/* Configure Integration Dialog */}
      <Dialog open={!!editingIntegration} onClose={() => setEditingIntegration(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Configure Integration: {editingIntegration?.name}</DialogTitle>
        <DialogContent>
          <Box display="flex" flexDirection="column" gap={2} pt={1}>
            {(integrationError || updateIntegrationMutation.isError) && (
              <Alert severity="error">{integrationError || 'Provider configuration could not be saved.'}</Alert>
            )}
            <FormControlLabel
              control={
                <Switch
                  checked={integrationEnabled}
                  onChange={(e) => setIntegrationEnabled(e.target.checked)}
                  color="primary"
                />
              }
              label="Enable Integration"
            />

            <Typography variant="caption" fontWeight={600} color="text.secondary">
              PROVIDER CREDENTIALS & CONFIG (JSON):
            </Typography>
            <TextField
              multiline
              rows={6}
              fullWidth
              value={integrationConfigJson}
              onChange={(e) => setIntegrationConfigJson(e.target.value)}
              sx={{ fontFamily: 'monospace', fontSize: '0.85rem' }}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditingIntegration(null)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleSaveIntegration}
            disabled={updateIntegrationMutation.isPending}
          >
            {updateIntegrationMutation.isPending ? <CircularProgress size={20} /> : 'Save Configuration'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
