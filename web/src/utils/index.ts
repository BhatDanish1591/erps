import { format, parseISO } from 'date-fns'

export function formatDate(iso: string, pattern = 'dd MMM yyyy'): string {
  try {
    return format(parseISO(iso), pattern)
  } catch {
    return iso
  }
}

export function formatDateTime(iso: string): string {
  return formatDate(iso, 'dd MMM yyyy, HH:mm')
}

export function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase()
}

export function toTitleCase(str: string): string {
  return str.toLowerCase().split('_').map(capitalize).join(' ')
}

export function truncate(str: string, maxLength = 50): string {
  return str.length > maxLength ? str.slice(0, maxLength) + '...' : str
}

export function buildQueryString(params: Record<string, unknown>): string {
  const qs = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== '') {
      qs.append(key, String(value))
    }
  }
  const str = qs.toString()
  return str ? `?${str}` : ''
}
