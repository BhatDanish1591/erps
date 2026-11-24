import { Platform } from 'react-native'

export const theme = {
  colors: {
    // Brand & Primary
    primary: '#2563eb',
    primaryLight: '#3b82f6',
    primaryDark: '#1d4ed8',
    primary50: '#eff6ff',
    primary100: '#dbeafe',
    primary200: '#bfdbfe',

    // Secondary / Accents
    secondary: '#7c3aed',
    secondary50: '#f5f3ff',
    secondary100: '#ede9fe',

    emerald: '#10b981',
    emerald50: '#ecfdf5',
    emerald100: '#d1fae5',

    amber: '#f59e0b',
    amber50: '#fffbeb',
    amber100: '#fef3c7',

    rose: '#f43f5e',
    rose50: '#fff1f2',
    rose100: '#ffe4e6',

    cyan: '#06b6d4',
    cyan50: '#ecfeff',
    cyan100: '#cffafe',

    // Neutral & Surfaces
    background: '#f8fafc',
    surface: '#ffffff',
    surfaceElevated: '#ffffff',
    surfaceSubtle: '#f1f5f9',

    // Text
    textPrimary: '#0f172a',
    textSecondary: '#475569',
    textMuted: '#64748b',
    textLight: '#94a3b8',
    textInverse: '#ffffff',

    // Borders & Dividers
    border: '#e2e8f0',
    borderSubtle: '#f1f5f9',
    borderStrong: '#cbd5e1',

    // Status
    success: '#16a34a',
    warning: '#d97706',
    danger: '#dc2626',
    info: '#0284c7',
  },

  typography: {
    fontFamilies: {
      sans: Platform.select({
        ios: 'System',
        android: 'Roboto',
        default: 'sans-serif',
      }),
    },
    sizes: {
      xs: 11,
      sm: 13,
      base: 15,
      lg: 17,
      xl: 20,
      '2xl': 24,
      '3xl': 30,
    },
    weights: {
      regular: '400' as const,
      medium: '500' as const,
      semibold: '600' as const,
      bold: '700' as const,
      heavy: '800' as const,
    },
  },

  radii: {
    xs: 6,
    sm: 10,
    md: 14,
    lg: 18,
    xl: 24,
    full: 9999,
  },

  shadows: {
    none: {
      shadowColor: 'transparent',
      shadowOffset: { width: 0, height: 0 },
      shadowOpacity: 0,
      shadowRadius: 0,
      elevation: 0,
    },
    sm: {
      shadowColor: '#0f172a',
      shadowOffset: { width: 0, height: 1 },
      shadowOpacity: 0.05,
      shadowRadius: 3,
      elevation: 1,
    },
    md: {
      shadowColor: '#0f172a',
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.06,
      shadowRadius: 10,
      elevation: 3,
    },
    lg: {
      shadowColor: '#0f172a',
      shadowOffset: { width: 0, height: 8 },
      shadowOpacity: 0.1,
      shadowRadius: 20,
      elevation: 6,
    },
    glow: (color: string) => ({
      shadowColor: color,
      shadowOffset: { width: 0, height: 6 },
      shadowOpacity: 0.25,
      shadowRadius: 12,
      elevation: 5,
    }),
  },
}
