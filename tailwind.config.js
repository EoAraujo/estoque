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
