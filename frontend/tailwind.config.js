/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Ink-navy base — deliberately not pure black.
        ink: {
          900: "#080b14",
          800: "#0c1120",
          700: "#121a2e",
          600: "#1a2438",
        },
        // Signature scanline cyan.
        scan: { DEFAULT: "#35e0d4", dim: "#1d8f88" },
        // Status accents.
        live: "#3ddc84",
        dead: "#5b6b86",
        warn: "#f5a623",
        risk: "#ff5c6c",
        edge: "#1e2a44", // hairline borders
      },
      fontFamily: {
        sans: ["var(--font-grotesk)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(53,224,212,0.25), 0 8px 30px -12px rgba(53,224,212,0.35)",
      },
    },
  },
  plugins: [],
};
