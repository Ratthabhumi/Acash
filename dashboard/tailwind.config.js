/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      // ACASH Warm Neutral Standard — semantic aliases backed by CSS custom
      // properties. Structural colors flip with the `.dark` class automatically;
      // `dark:` variants are only needed for semantic status colors.
      colors: {
        app: 'rgb(var(--bg-app-rgb) / <alpha-value>)',
        surface: {
          DEFAULT: 'rgb(var(--bg-surface-rgb) / <alpha-value>)',
          muted: 'rgb(var(--bg-surface-muted-rgb) / <alpha-value>)',
          hover: 'rgb(var(--bg-surface-hover-rgb) / <alpha-value>)',
        },
        border: {
          DEFAULT: 'rgb(var(--border-default-rgb) / <alpha-value>)',
          subtle: 'rgb(var(--border-subtle-rgb) / <alpha-value>)',
          strong: 'rgb(var(--border-strong-rgb) / <alpha-value>)',
          focus: 'rgb(var(--accent-rgb) / <alpha-value>)',
        },
        default: 'rgb(var(--border-default-rgb) / <alpha-value>)',
        primary: 'rgb(var(--text-primary-rgb) / <alpha-value>)',
        secondary: 'rgb(var(--text-secondary-rgb) / <alpha-value>)',
        muted: 'rgb(var(--text-muted-rgb) / <alpha-value>)',
        accent: {
          DEFAULT: 'rgb(var(--accent-rgb) / <alpha-value>)',
          hover: 'rgb(var(--accent-hover-rgb) / <alpha-value>)',
          subtle: 'rgb(var(--accent-subtle-rgb) / <alpha-value>)',
        },
        // Legacy structural keys retained for compatibility, repointed to the
        // Warm Neutral tokens so any residual usage stays on-palette.
        background: 'rgb(var(--bg-app-rgb) / <alpha-value>)',
        brand: {
          DEFAULT: 'rgb(var(--accent-rgb) / <alpha-value>)',
          subtle: 'rgb(var(--accent-subtle-rgb) / <alpha-value>)',
          border: 'rgb(var(--accent-rgb) / <alpha-value>)',
          dark: 'rgb(var(--accent-hover-rgb) / <alpha-value>)',
        },
        // Semantic status palette — health/verdict colors, unchanged.
        semantic: {
          success: "#15803d",
          "success-bg": "#f0fdf4",
          "success-border": "#bbf7d0",
          error: "#b91c1c",
          "error-bg": "#fef2f2",
          "error-border": "#fecaca",
          warning: "#b45309",
          "warning-bg": "#fffbeb",
          "warning-border": "#fde68a",
          info: "#1d4ed8",
          "info-bg": "#eff6ff",
          "info-border": "#bfdbfe",
          muted: "#64748b",
          "muted-bg": "#f8fafc",
          "muted-border": "#e2e8f0",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        mono: [
          "JetBrains Mono",
          "Fira Code",
          "SF Mono",
          "Cascadia Code",
          "Consolas",
          "monospace",
        ],
      },
    },
  },
  plugins: [],
}