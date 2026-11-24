import { PageHeader } from '@/components/ui/PageHeader'
import { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Grid,
  Typography,
  Chip,
  Button,
  Tabs,
  Tab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Divider,
  Switch,
  FormControlLabel,
  MenuItem,
} from '@mui/material'
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive'
import HubIcon from '@mui/icons-material/Hub'
import SettingsSuggestIcon from '@mui/icons-material/SettingsSuggest'
import MarkEmailReadIcon from '@mui/icons-material/MarkEmailRead'
import WhatsAppIcon from '@mui/icons-material/WhatsApp'
import SmsIcon from '@mui/icons-material/Sms'
import CloudDoneIcon from '@mui/icons-material/CloudDone'
import SyncIcon from '@mui/icons-material/Sync'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'

import {
  notificationsApi,
  NotificationTemplate,
  NotificationOutboxEntry,
  NotificationLogEntry,
  UserNotificationPreference,
} from '../../api/notifications'
import {
  integrationsApi,
  TenantIntegrationItem,
} from '../../api/integrations'

const PROVIDER_METAS = [
  { type: 'EMAIL_RESEND', name: 'Resend Email API', channel: 'Email', icon: <MarkEmailReadIcon color="primary" /> },
  { type: 'EMAIL_SES', name: 'Amazon SES', channel: 'Email', icon: <MarkEmailReadIcon color="primary" /> },
  { type: 'WHATSAPP_META', name: 'Meta WhatsApp Cloud API', channel: 'WhatsApp', icon: <WhatsAppIcon color="success" /> },
  { type: 'SMS_MSG91', name: 'MSG91 SMS & OTP', channel: 'SMS', icon: <SmsIcon color="warning" /> },
  { type: 'PUSH_FIREBASE', name: 'Firebase Cloud Messaging', channel: 'Push', icon: <NotificationsActiveIcon color="error" /> },
  { type: 'PAYMENT_RAZORPAY', name: 'Razorpay Payment Gateway', channel: 'Payment', icon: <CloudDoneIcon color="info" /> },
  { type: 'STORAGE_S3', name: 'Amazon S3 Object Storage', channel: 'Storage', icon: <CloudDoneIcon color="secondary" /> },
]

export default function NotificationIntegrationPage() {
  const [tabIndex, setTabIndex] = useState<number>(0)
  const [loading, setLoading] = useState<boolean>(true)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  // Data states
  const [integrations, setIntegrations] = useState<TenantIntegrationItem[]>([])
  const [templates, setTemplates] = useState<NotificationTemplate[]>([])
  const [outbox, setOutbox] = useState<NotificationOutboxEntry[]>([])
  const [logs, setLogs] = useState<NotificationLogEntry[]>([])
  const [preferences, setPreferences] = useState<UserNotificationPreference | null>(null)

  // Configure Modal
  const [openConfigDialog, setOpenConfigDialog] = useState<boolean>(false)
  const [selectedProvider, setSelectedProvider] = useState<string>('WHATSAPP_META')
  const [apiKeyOrToken, setApiKeyOrToken] = useState<string>('')
  const [senderOrPhoneId, setSenderOrPhoneId] = useState<string>('')
  const [savingConfig, setSavingConfig] = useState<boolean>(false)

  // Test Probe Modal
  const [testingProvider, setTestingProvider] = useState<string | null>(null)
  const [testRecipient, setTestRecipient] = useState<string>('')
  const [runningTest, setRunningTest] = useState<boolean>(false)

  useEffect(() => {
    loadAllData()
  }, [])

  const loadAllData = async () => {
    setLoading(true)
    setErrorMsg(null)
    try {
      const [intList, tmplList, outList, logList, pref] = await Promise.all([
        integrationsApi.list(),
        notificationsApi.listTemplates(),
        notificationsApi.listOutbox(50),
        notificationsApi.listLogs({ limit: 50 }),
        notificationsApi.getPreferences(),
      ])
      setIntegrations(intList)
      setTemplates(tmplList)
      setOutbox(outList)
      setLogs(logList)
      setPreferences(pref)
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load notification architecture data.')
    } finally {
      setLoading(false)
    }
  }

  const handleSaveIntegration = async () => {
    setSavingConfig(true)
    setErrorMsg(null)
    setSuccessMsg(null)
    try {
      await integrationsApi.configure({
        provider_type: selectedProvider,
        is_enabled: true,
        credentials: {
          access_token: apiKeyOrToken,
          api_key: apiKeyOrToken,
          phone_number_id: senderOrPhoneId,
        },
        settings: {
          sender_id: senderOrPhoneId,
        },
      })
      setSuccessMsg(`Integration ${selectedProvider} configured successfully.`)
      setOpenConfigDialog(false)
      setApiKeyOrToken('')
      setSenderOrPhoneId('')
      const updated = await integrationsApi.list()
      setIntegrations(updated)
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to save integration.')
    } finally {
      setSavingConfig(false)
    }
  }

  const handleRunTestProbe = async (providerType: string) => {
    setRunningTest(true)
    setErrorMsg(null)
    setSuccessMsg(null)
    try {
      const res = await integrationsApi.testConnection(providerType, testRecipient || undefined)
      if (res.success) {
        setSuccessMsg(`Test connection succeeded: ${res.message}`)
      } else {
        setErrorMsg(`Test connection failed: ${res.message}`)
      }
      setTestingProvider(null)
      setTestRecipient('')
      const updated = await integrationsApi.list()
      setIntegrations(updated)
    } catch (err: any) {
      setErrorMsg(err.message || 'Test probe execution failed.')
    } finally {
      setRunningTest(false)
    }
  }

  const handleTriggerOutboxBatch = async () => {
    try {
      const res = await notificationsApi.processOutboxBatch(50)
      setSuccessMsg(`Worker processed ${res.processed_count} outbox entries.`)
      const updatedOut = await notificationsApi.listOutbox(50)
      const updatedLogs = await notificationsApi.listLogs({ limit: 50 })
      setOutbox(updatedOut)
      setLogs(updatedLogs)
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to process outbox batch.')
    }
  }

  const handlePreferenceChange = async (field: keyof UserNotificationPreference, value: boolean) => {
    if (!preferences) return
    const updated = { ...preferences, [field]: value }
    setPreferences(updated)
    try {
      await notificationsApi.updatePreferences({ [field]: value })
    } catch (err: any) {
      setErrorMsg('Failed to update preferences.')
    }
  }

  return (
    <Box>
      {/* Page Header */}
      <Box sx={{ mb: 3 }}>
        <PageHeader
          title="Notifications & Integrations"
          description="Manage notification channels, templates, providers, and delivery logs."
          icon={<SyncIcon />}
        >
          <Button
            variant="contained"
            startIcon={<SyncIcon />}
            onClick={loadAllData}
            disabled={loading}
          >
            Refresh All
          </Button>
        </PageHeader>
      </Box>

      {/* Messages */}
      {errorMsg && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setErrorMsg(null)}>
          {errorMsg}
        </Alert>
      )}
      {successMsg && (
        <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSuccessMsg(null)}>
          {successMsg}
        </Alert>
      )}

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={tabIndex} onChange={(_, val) => setTabIndex(val)} variant="scrollable">
          <Tab icon={<HubIcon />} iconPosition="start" label="Provider Integrations" />
          <Tab icon={<NotificationsActiveIcon />} iconPosition="start" label="Notification Templates" />
          <Tab icon={<PlayArrowIcon />} iconPosition="start" label="Transactional Outbox" />
          <Tab icon={<CloudDoneIcon />} iconPosition="start" label="Delivery Logs" />
          <Tab icon={<SettingsSuggestIcon />} iconPosition="start" label="My Notification Preferences" />
        </Tabs>
      </Box>

      {loading ? (
        <Box display="flex" justifyContent="center" py={8}>
          <CircularProgress />
        </Box>
      ) : (
        <>
          {/* TAB 0: Provider Integrations */}
          {tabIndex === 0 && (
            <Grid container spacing={3}>
              {PROVIDER_METAS.map((prov) => {
                const config = integrations.find((i) => i.provider_type === prov.type)
                const isConfigured = !!config
                const isActive = config?.status === 'ACTIVE'
                return (
                  <Grid item xs={12} sm={6} md={4} key={prov.type}>
                    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                      <CardContent sx={{ flexGrow: 1 }}>
                        <Box display="flex" justifyContent="space-between" alignItems="center" mb={1.5}>
                          <Box display="flex" alignItems="center" gap={1}>
                            {prov.icon}
                            <Typography variant="h6" fontWeight={700}>
                              {prov.name}
                            </Typography>
                          </Box>
                          <Chip
                            size="small"
                            label={config ? config.status : 'NOT CONFIGURED'}
                            color={isActive ? 'success' : isConfigured ? 'warning' : 'default'}
                          />
                        </Box>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                          Channel: <strong>{prov.channel}</strong> · Multi-Tenant Gateway
                        </Typography>

                        {config?.masked_credentials && (
                          <Box sx={{ bgcolor: 'action.hover', p: 1, borderRadius: 1, mb: 2 }}>
                            <Typography variant="caption" color="text.secondary" display="block">
                              Masked Credentials:
                            </Typography>
                            {Object.entries(config.masked_credentials).map(([k, v]) => (
                              <Typography key={k} variant="caption" fontWeight={600} display="block">
                                {k}: {v}
                              </Typography>
                            ))}
                          </Box>
                        )}

                        {config?.last_tested_at && (
                          <Typography variant="caption" color="text.secondary" display="block">
                            Last tested: {new Date(config.last_tested_at).toLocaleString()}
                          </Typography>
                        )}
                      </CardContent>

                      <Box sx={{ p: 2, pt: 0, display: 'flex', gap: 1 }}>
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => {
                            setSelectedProvider(prov.type)
                            setOpenConfigDialog(true)
                          }}
                        >
                          Configure
                        </Button>
                        <Button
                          size="small"
                          variant="contained"
                          color="secondary"
                          onClick={() => setTestingProvider(prov.type)}
                          disabled={!isConfigured}
                        >
                          Test Probe
                        </Button>
                      </Box>
                    </Card>
                  </Grid>
                )
              })}
            </Grid>
          )}

          {/* TAB 1: Notification Templates */}
          {tabIndex === 1 && (
            <Card>
              <CardContent>
                <Typography variant="h6" fontWeight={600} gutterBottom>
                  Pre-configured & Approved Templates
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Templates map domain events to approved channel formats with dynamic placeholder interpolation.
                </Typography>
                <TableContainer component={Paper} variant="outlined" sx={{ overflowX: 'auto', width: '100%' }}>
                  <Table size="small" sx={{ minWidth: 600 }}>
                    <TableHead>
                      <TableRow sx={{ bgcolor: 'action.hover' }}>
                        <TableCell><strong>Event Type</strong></TableCell>
                        <TableCell><strong>Channel</strong></TableCell>
                        <TableCell><strong>Template Name</strong></TableCell>
                        <TableCell><strong>Subject / Content</strong></TableCell>
                        <TableCell><strong>External Approval</strong></TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {templates.map((t) => (
                        <TableRow key={t.id}>
                          <TableCell><Chip size="small" label={t.event_type} /></TableCell>
                          <TableCell><Chip size="small" label={t.channel} color="primary" variant="outlined" /></TableCell>
                          <TableCell><strong>{t.name}</strong></TableCell>
                          <TableCell sx={{ maxWidth: 350 }}>
                            {t.subject_template && <Typography variant="caption" display="block" fontWeight={600}>Subj: {t.subject_template}</Typography>}
                            <Typography variant="body2">{t.body_template}</Typography>
                          </TableCell>
                          <TableCell>
                            {t.whatsapp_template_name && <Chip size="small" label={`WhatsApp: ${t.whatsapp_template_name}`} color="success" />}
                            {t.msg91_template_id && <Chip size="small" label={`DLT ID: ${t.msg91_template_id}`} color="warning" />}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          )}

          {/* TAB 2: Transactional Outbox */}
          {tabIndex === 2 && (
            <Box>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6" fontWeight={600}>
                  Transactional Outbox Queue
                </Typography>
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<PlayArrowIcon />}
                  onClick={handleTriggerOutboxBatch}
                >
                  Trigger Worker Dispatch
                </Button>
              </Box>

              <TableContainer component={Paper} variant="outlined" sx={{ overflowX: 'auto', width: '100%' }}>
                <Table size="small" sx={{ minWidth: 600 }}>
                  <TableHead>
                    <TableRow sx={{ bgcolor: 'action.hover' }}>
                      <TableCell><strong>Outbox ID</strong></TableCell>
                      <TableCell><strong>Event Type</strong></TableCell>
                      <TableCell><strong>Status</strong></TableCell>
                      <TableCell><strong>Retries</strong></TableCell>
                      <TableCell><strong>Idempotency Key</strong></TableCell>
                      <TableCell><strong>Created At</strong></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {outbox.length > 0 ? (
                      outbox.map((item) => (
                        <TableRow key={item.id}>
                          <TableCell><Typography variant="caption">{item.id.slice(0, 8)}...</Typography></TableCell>
                          <TableCell><strong>{item.event_type}</strong></TableCell>
                          <TableCell>
                            <Chip
                              size="small"
                              label={item.status}
                              color={
                                item.status === 'PROCESSED'
                                  ? 'success'
                                  : item.status === 'PROCESSING'
                                  ? 'info'
                                  : item.status === 'FAILED'
                                  ? 'error'
                                  : 'warning'
                              }
                            />
                          </TableCell>
                          <TableCell>{item.retry_count} / {item.max_retries}</TableCell>
                          <TableCell><Typography variant="caption">{item.idempotency_key.slice(0, 16)}...</Typography></TableCell>
                          <TableCell>{new Date(item.created_at).toLocaleString()}</TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={6} align="center">No outbox entries found.</TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          )}

          {/* TAB 3: Delivery Logs */}
          {tabIndex === 3 && (
            <Card>
              <CardContent>
                <Typography variant="h6" fontWeight={600} gutterBottom>
                  Multi-Channel Notification Audit & Delivery Logs
                </Typography>
                <TableContainer component={Paper} variant="outlined" sx={{ overflowX: 'auto', width: '100%' }}>
                  <Table size="small" sx={{ minWidth: 600 }}>
                    <TableHead>
                      <TableRow sx={{ bgcolor: 'action.hover' }}>
                        <TableCell><strong>Timestamp</strong></TableCell>
                        <TableCell><strong>Channel</strong></TableCell>
                        <TableCell><strong>Provider</strong></TableCell>
                        <TableCell><strong>Recipient</strong></TableCell>
                        <TableCell><strong>Event</strong></TableCell>
                        <TableCell><strong>Provider Msg ID</strong></TableCell>
                        <TableCell><strong>Delivery Status</strong></TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {logs.length > 0 ? (
                        logs.map((log) => (
                          <TableRow key={log.id}>
                            <TableCell>{new Date(log.created_at).toLocaleTimeString()}</TableCell>
                            <TableCell><Chip size="small" label={log.channel} /></TableCell>
                            <TableCell>{log.provider}</TableCell>
                            <TableCell><strong>{log.recipient}</strong></TableCell>
                            <TableCell>{log.event_type}</TableCell>
                            <TableCell><Typography variant="caption">{log.provider_message_id || '—'}</Typography></TableCell>
                            <TableCell>
                              <Chip
                                size="small"
                                label={log.status}
                                color={
                                  log.status === 'DELIVERED' || log.status === 'READ'
                                    ? 'success'
                                    : log.status === 'DISPATCHED'
                                    ? 'info'
                                    : 'error'
                                }
                              />
                            </TableCell>
                          </TableRow>
                        ))
                      ) : (
                        <TableRow>
                          <TableCell colSpan={7} align="center">No notification delivery logs recorded.</TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          )}

          {/* TAB 4: My Notification Preferences */}
          {tabIndex === 4 && preferences && (
            <Card>
              <CardContent>
                <Typography variant="h6" fontWeight={600} gutterBottom>
                  User Notification Channels & Quiet Hours
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                  Customize which communication channels and event categories you consent to receive.
                </Typography>

                <Grid container spacing={4}>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" fontWeight={700} gutterBottom>
                      Channel Opt-Ins
                    </Typography>
                    <Divider sx={{ mb: 2 }} />
                    <FormControlLabel
                      control={<Switch checked={preferences.channel_email} onChange={(e) => handlePreferenceChange('channel_email', e.target.checked)} />}
                      label="Email Notifications (SES / Resend)"
                    />
                    <br />
                    <FormControlLabel
                      control={<Switch checked={preferences.channel_whatsapp} onChange={(e) => handlePreferenceChange('channel_whatsapp', e.target.checked)} />}
                      label="WhatsApp Messages (Meta Cloud API)"
                    />
                    <br />
                    <FormControlLabel
                      control={<Switch checked={preferences.channel_sms} onChange={(e) => handlePreferenceChange('channel_sms', e.target.checked)} />}
                      label="SMS & OTP Alerts (MSG91)"
                    />
                    <br />
                    <FormControlLabel
                      control={<Switch checked={preferences.channel_push} onChange={(e) => handlePreferenceChange('channel_push', e.target.checked)} />}
                      label="Mobile Push Notifications (Firebase FCM / APNs)"
                    />
                    <br />
                    <FormControlLabel
                      control={<Switch checked={preferences.channel_in_app} onChange={(e) => handlePreferenceChange('channel_in_app', e.target.checked)} />}
                      label="In-App Bell Alerts"
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" fontWeight={700} gutterBottom>
                      Event Category Preferences
                    </Typography>
                    <Divider sx={{ mb: 2 }} />
                    <FormControlLabel
                      control={<Switch checked={preferences.category_attendance} onChange={(e) => handlePreferenceChange('category_attendance', e.target.checked)} />}
                      label="Attendance & Absence Alerts"
                    />
                    <br />
                    <FormControlLabel
                      control={<Switch checked={preferences.category_examinations} onChange={(e) => handlePreferenceChange('category_examinations', e.target.checked)} />}
                      label="Examinations & Results Announcements"
                    />
                    <br />
                    <FormControlLabel
                      control={<Switch checked={preferences.category_finance} onChange={(e) => handlePreferenceChange('category_finance', e.target.checked)} />}
                      label="Fee Due Reminders & Payment Receipts"
                    />
                    <br />
                    <FormControlLabel
                      control={<Switch checked={preferences.category_academic} onChange={(e) => handlePreferenceChange('category_academic', e.target.checked)} />}
                      label="Academic LMS, Materials, & Timetables"
                    />
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Configure Provider Modal */}
      <Dialog open={openConfigDialog} onClose={() => setOpenConfigDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>
          Configure {selectedProvider}
        </DialogTitle>
        <DialogContent dividers>
          <TextField
            select
            fullWidth
            label="Integration Provider"
            value={selectedProvider}
            onChange={(e) => setSelectedProvider(e.target.value)}
            sx={{ mb: 2 }}
          >
            {PROVIDER_METAS.map((p) => (
              <MenuItem key={p.type} value={p.type}>
                {p.name}
              </MenuItem>
            ))}
          </TextField>

          <TextField
            fullWidth
            label="API Key / Auth Token / Secret"
            type="password"
            placeholder="Enter secure provider API key or bearer token"
            value={apiKeyOrToken}
            onChange={(e) => setApiKeyOrToken(e.target.value)}
            sx={{ mb: 2 }}
          />

          <TextField
            fullWidth
            label="Phone Number ID / Sender ID / WABA ID"
            placeholder="e.g. 100987654321098 or EDUSAS"
            value={senderOrPhoneId}
            onChange={(e) => setSenderOrPhoneId(e.target.value)}
            sx={{ mb: 2 }}
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={() => setOpenConfigDialog(false)} disabled={savingConfig}>
            Cancel
          </Button>
          <Button variant="contained" onClick={handleSaveIntegration} disabled={savingConfig}>
            {savingConfig ? 'Saving...' : 'Save Configuration'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Test Probe Modal */}
      <Dialog open={!!testingProvider} onClose={() => setTestingProvider(null)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>
          Run Test Connection Probe
        </DialogTitle>
        <DialogContent dividers>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Send a sample verification ping to check credentials and endpoint connectivity for {testingProvider}.
          </Typography>
          <TextField
            fullWidth
            label="Test Destination (Email or Phone Number)"
            placeholder="e.g. 919876543210 or admin@example.com"
            value={testRecipient}
            onChange={(e) => setTestRecipient(e.target.value)}
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={() => setTestingProvider(null)} disabled={runningTest}>
            Cancel
          </Button>
          <Button
            variant="contained"
            color="secondary"
            onClick={() => testingProvider && handleRunTestProbe(testingProvider)}
            disabled={runningTest}
          >
            {runningTest ? 'Executing Probe...' : 'Send Test Ping'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
