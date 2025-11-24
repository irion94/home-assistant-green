/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0f0f0f',
        surface: '#1a1a1a',
        'surface-light': '#2a2a2a',
        primary: '#3b82f6',
        'primary-dark': '#2563eb',
        secondary: '#6366f1',
        success: '#22c55e',
        warning: '#f59e0b',
        error: '#ef4444',
        'text-primary': '#ffffff',
        'text-secondary': '#a1a1aa',
      },
      fontSize: {
        'kiosk-sm': '1rem',
        'kiosk-base': '1.125rem',
        'kiosk-lg': '1.5rem',
        'kiosk-xl': '2rem',
        'kiosk-2xl': '3rem',
        'kiosk-3xl': '4rem',
      },
      spacing: {
        'touch': '48px',
      },
      borderRadius: {
        'card': '16px',
      },
    },
  },
  plugins: [],
}
