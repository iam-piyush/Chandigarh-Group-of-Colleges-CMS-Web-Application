/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/*.html"
  ],
  theme: {
    screens: {
      'mdForBanner': '880px',
      'smForBanner': '580px',
      'xsForBanner': '488px',
      'sm': '640px',
      'md': '768px',
      'lg': '1024px',
      'xl': '1280px',
      '2xl': '1536px',
    },
  },
  plugins: [
    require('@tailwindcss/forms')
  ],
}

