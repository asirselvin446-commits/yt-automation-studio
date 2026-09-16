/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        studio: {
          bg: '#090a0f',
          card: '#12141c',
          'card-hover': '#181b26',
          border: '#232738',
          accent: '#6366f1',
          'accent-glow': '#4f46e5',
          yt: '#ff0033',
          success: '#10b981',
          warning: '#f59e0b',
          danger: '#ef4444',
          text: '#f8fafc',
          muted: '#94a3b8',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
