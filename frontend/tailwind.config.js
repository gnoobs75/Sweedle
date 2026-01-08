/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Background colors
        background: {
          DEFAULT: '#0f0f1a',
          secondary: '#1a1a2e',
        },
        // Surface colors
        surface: {
          DEFAULT: '#1e1e32',
          light: '#252542',
          lighter: '#2a2a4a',
        },
        // Border
        border: {
          DEFAULT: '#2a2a44',
        },
        // Text colors
        text: {
          primary: '#ffffff',
          secondary: '#a0a0b8',
          muted: '#6b6b80',
        },
        // Primary brand color
        primary: {
          DEFAULT: '#6366f1',
          hover: '#818cf8',
          active: '#4f46e5',
        },
        // Accent color
        accent: {
          DEFAULT: '#22d3ee',
          hover: '#67e8f9',
        },
        // Semantic colors
        success: {
          DEFAULT: '#22c55e',
        },
        warning: {
          DEFAULT: '#f59e0b',
        },
        error: {
          DEFAULT: '#ef4444',
        },
        info: {
          DEFAULT: '#3b82f6',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'spin-slow': 'spin 3s linear infinite',
        'pulse-soft': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'progress-indeterminate': 'progress-indeterminate 1.5s ease-in-out infinite',
      },
      keyframes: {
        'progress-indeterminate': {
          '0%': { transform: 'translateX(-100%)' },
          '50%': { transform: 'translateX(100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
      },
    },
  },
  plugins: [],
};
