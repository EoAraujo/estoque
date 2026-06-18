/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    "./templates/**/*.html",
    "./core/**/*.py",
    "./accounts/**/*.py",
    "./stock/**/*.py",
    "./intelligence/**/*.py",
    "./audit/**/*.py",
    "./reports/**/*.py",
    "./notifications/**/*.py",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#ecfdf5',
          100: '#d1fae5',
          200: '#a7f3d0',
          300: '#6ee7b7',
          400: '#34d399',
          500: '#10b981',
          600: '#059669',
          700: '#047857',
          800: '#065f46',
          900: '#064e3b',
        },
        surface: {
          0:   '#0C0C0D',
          50:  '#111114',
          100: '#161619',
          200: '#1A1A1E',
          300: '#222226',
          400: '#2A2A2E',
          500: '#333338',
          600: '#3D3D42',
          700: '#52525B',
          800: '#71717A',
          900: '#A1A1AA',
        },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms')({ strategy: 'class' }),
  ],
}
