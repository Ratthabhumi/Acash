/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#f8fafc", // slate-50
        surface: {
          DEFAULT: "#ffffff",
          subtle: "#f1f5f9", // slate-100
          hover: "#f8fafc",
        },
        border: {
          DEFAULT: "#e2e8f0", // slate-200
          subtle: "#edf2f7",
          focus: "#94a3b8",
        },
        charcoal: {
          900: "#0f172a", // primary text
          700: "#334155", // secondary heading
          500: "#64748b", // body secondary
          400: "#94a3b8", // tertiary / muted
          300: "#cbd5e1", // disabled / subtle
        },
        // Muted semantic enterprise accents
        brand: {
          DEFAULT: "#15803d", // emerald-700
          subtle: "#ecfdf5",  // emerald-50
          border: "#a7f3d0",  // emerald-200
          dark: "#166534",
        },
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
