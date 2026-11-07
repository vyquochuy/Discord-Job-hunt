/** @type {import('tailwindcss').Config} */

// Colour tokens are CSS variables (RGB triplets) so a single class name resolves
// to the right colour in each of the 3 themes (enterprise / glass / ai).
const alpha = (name) => `rgb(var(--${name}-rgb) / <alpha-value>)`;
const translucent = (name) => `rgb(var(--${name}-rgb) / var(--${name}-alpha))`;

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: alpha('primary'),
          hover: alpha('primary-hover'),
          50: alpha('primary-50'),
          100: alpha('primary-100'),
          200: alpha('primary-200'),
          300: alpha('primary-300'),
          400: alpha('primary-400'),
          500: alpha('primary-500'),
          600: alpha('primary-600'),
          700: alpha('primary-700'),
          800: alpha('primary-800'),
          900: alpha('primary-900'),
        },
        background: 'var(--bg)',
        surface: {
          DEFAULT: translucent('surface'),
          muted: translucent('surface-muted'),
          subtle: translucent('surface-2'),
        },
        'surface-solid': alpha('surface-solid'),
        'surface-2': translucent('surface-2'),
        text: {
          primary: alpha('text'),
          secondary: alpha('text-secondary'),
          muted: alpha('text-muted'),
        },
        border: {
          DEFAULT: translucent('line'),
          subtle: alpha('line-subtle'),
          strong: alpha('line-strong'),
        },
        success: {
          DEFAULT: alpha('success'),
          50: alpha('success-50'),
          100: alpha('success-100'),
          600: alpha('success-600'),
          700: alpha('success-700'),
        },
        warning: {
          DEFAULT: alpha('warning'),
          50: alpha('warning-50'),
          100: alpha('warning-100'),
          600: alpha('warning-600'),
          700: alpha('warning-700'),
        },
        danger: {
          DEFAULT: alpha('danger'),
          50: alpha('danger-50'),
          100: alpha('danger-100'),
          600: alpha('danger-600'),
          700: alpha('danger-700'),
        },
        critical: {
          DEFAULT: alpha('critical'),
          50: alpha('critical-50'),
          800: alpha('critical-800'),
        },
        violet: {
          DEFAULT: alpha('violet'),
          50: alpha('violet-50'),
          100: alpha('violet-100'),
          200: alpha('violet-200'),
          500: alpha('violet-500'),
          600: alpha('violet-600'),
          700: alpha('violet-700'),
        },
        cyan: {
          DEFAULT: alpha('cyan'),
          50: alpha('cyan-50'),
          100: alpha('cyan-100'),
          500: alpha('cyan-500'),
          600: alpha('cyan-600'),
        },
        green: alpha('green'),
        overlay: alpha('overlay'),
        scrim: 'var(--scrim)',
        terminal: {
          DEFAULT: 'var(--code-bg)',
          foreground: 'var(--code-text)',
        },
      },
      fontFamily: {
        sans: ['DM Sans', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        display: ['Manrope', 'DM Sans', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        subtle: 'var(--shadow-subtle)',
        card: 'var(--shadow-card)',
        elevated: 'var(--shadow-elevated)',
        dialog: 'var(--shadow-dialog)',
        primary: 'var(--shadow-primary)',
      },
      borderRadius: {
        xs: 'var(--radius-xs)',
        sm: 'var(--radius-sm)',
        DEFAULT: 'var(--radius-sm)',
        md: 'var(--radius-control)',
        lg: 'var(--radius-card)',
        xl: 'var(--radius-xl)',
        '2xl': 'var(--radius-2xl)',
        '3xl': 'var(--radius-2xl)',
      },
      ringColor: {
        DEFAULT: alpha('primary'),
      },
    },
  },
  plugins: [],
};
