/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        parchment: "#f5f4ed",
        ivory: "#faf9f5",
        "warm-sand": "#e8e6dc",
        "border-cream": "#f0eee6",
        "anthropic-near-black": "#141413",
        terracotta: "#c96442",
        "coral-accent": "#d97757",
        "error-crimson": "#b53333",
        "focus-blue": "#3898ec",
        "dark-surface": "#30302e",
        "charcoal-warm": "#4d4c48",
        "olive-gray": "#5e5d59",
        "stone-gray": "#87867f",
        "dark-warm": "#3d3d3a",
        "warm-silver": "#b0aea5",
        "border-warm": "#e8e6dc",
        "border-dark": "#30302e",
      },
      fontFamily: {
        "anthropic-serif": ["Anthropic Serif", "Georgia", "serif"],
        "anthropic-sans": ["Anthropic Sans", "Arial", "sans-serif"],
        "anthropic-mono": ["Anthropic Mono", "Arial", "monospace"],
      },
      boxShadow: {
        "whisper": "0px 4px 24px rgba(0,0,0,0.05)",
        "ring-warm": "0px 0px 0px 1px #d1cfc5",
        "ring-subtle": "0px 0px 0px 1px #dedc01",
        "ring-deep": "0px 0px 0px 1px #c2c0b6",
        "ring-terracotta": "0px 0px 0px 1px #c96442",
        "ring-border": "0px 0px 0px 1px #e8e6dc",
      },
      borderRadius: {
        "sharp": "4px",
        "subtly-rounded": "6px",
        "comfortably-rounded": "8px",
        "generously-rounded": "12px",
        "very-rounded": "16px",
        "highly-rounded": "24px",
        "maximum-rounded": "32px",
      }
    },
  },
  plugins: [],
}

