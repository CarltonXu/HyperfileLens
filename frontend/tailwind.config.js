/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}'
  ],
  theme: {
    extend: {
      colors: {
        // Use CSS variables for semantic colors
        background: 'rgb(var(--background-rgb) / <alpha-value>)',
        'background-secondary': 'rgb(var(--background-secondary-rgb) / <alpha-value>)',
        'background-tertiary': 'rgb(var(--background-tertiary-rgb) / <alpha-value>)',

        foreground: 'rgb(var(--foreground-rgb) / <alpha-value>)',
        'foreground-secondary': 'rgb(var(--foreground-secondary-rgb) / <alpha-value>)',
        'foreground-tertiary': 'rgb(var(--foreground-tertiary-rgb) / <alpha-value>)',
        'foreground-muted': 'rgb(var(--foreground-muted-rgb) / <alpha-value>)',

        border: 'rgb(var(--border-rgb) / <alpha-value>)',
        'border-secondary': 'rgb(var(--border-secondary-rgb) / <alpha-value>)',

        card: 'rgb(var(--card-rgb) / <alpha-value>)',
        'card-secondary': 'rgb(var(--card-secondary-rgb) / <alpha-value>)',

        hover: 'rgb(var(--hover-rgb) / <alpha-value>)',
        'hover-secondary': 'rgb(var(--hover-secondary-rgb) / <alpha-value>)',

        primary: {
          DEFAULT: 'rgb(var(--primary-rgb) / <alpha-value>)',
          foreground: 'rgb(var(--primary-foreground-rgb) / <alpha-value>)',
          light: 'rgb(var(--primary-light-rgb) / <alpha-value>)',
          // Keep existing shades for compatibility
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#172554'
        },
        success: {
          DEFAULT: 'rgb(var(--success-rgb) / <alpha-value>)',
          light: 'rgb(var(--success-light-rgb) / <alpha-value>)',
          50: '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d'
        },
        warning: {
          DEFAULT: 'rgb(var(--warning-rgb) / <alpha-value>)',
          light: 'rgb(var(--warning-light-rgb) / <alpha-value>)',
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f'
        },
        danger: {
          DEFAULT: 'rgb(var(--danger-rgb) / <alpha-value>)',
          light: 'rgb(var(--danger-light-rgb) / <alpha-value>)',
          50: '#fef2f2',
          100: '#fee2e2',
          200: '#fecaca',
          300: '#fca5a5',
          400: '#f87171',
          500: '#ef4444',
          600: '#dc2626',
          700: '#b91c1c',
          800: '#991b1b',
          900: '#7f1d1d'
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace']
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 3s linear infinite'
      }
    }
  },
  plugins: []
}
