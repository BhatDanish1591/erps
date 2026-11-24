import { Chip } from '@mui/material'
import type { ChipProps } from '@mui/material'

type Status = 'active' | 'inactive' | 'pending' | 'suspended' | 'error' | string

const STATUS_CONFIG: Record<string, { label: string; color: ChipProps['color'] }> = {
  active:    { label: 'Active',    color: 'success' },
  inactive:  { label: 'Inactive',  color: 'default' },
  pending:   { label: 'Pending',   color: 'warning' },
  suspended: { label: 'Suspended', color: 'error' },
  error:     { label: 'Error',     color: 'error' },
}

interface StatusChipProps {
  status: Status
  size?: ChipProps['size']
}

export function StatusChip({ status, size = 'small' }: StatusChipProps) {
  const config = STATUS_CONFIG[status.toLowerCase()] ?? {
    label: status,
    color: 'default' as const,
  }
  return <Chip label={config.label} color={config.color} size={size} />
}
