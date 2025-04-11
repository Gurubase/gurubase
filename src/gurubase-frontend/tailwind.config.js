import defaultTheme from "tailwindcss/defaultTheme";

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class", '[data-theme="dark"]'],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  safelist: [
    // Trust score colors
    "bg-emerald-500",
    "text-emerald-500",
    "bg-green-500",
    "text-green-500",
    "bg-lime-500",
    "text-lime-500",
    "bg-yellow-500",
    "text-yellow-500",
    "bg-orange-400",
    "text-orange-400",
    "bg-orange-500",
    "text-orange-500",
    "bg-red-400",
    "text-red-400",
    "bg-red-500",
    "text-red-500",
    "bg-red-600",
    "text-red-600"
  ],
  theme: {
    extend: {
      colors: {
        gray: {
          0: "#FFFFFF",
          25: "#FAFAFA",
          50: "#F0F1F3",
          75: "#F2F3F5",
          85: "#E2E2E2",
          90: "#DFE5EC",
          100: "#D1D4DA",
          200: "#BABFC8",
          300: "#9AA6B8",
          400: "#6D6D6D",
          500: "#697488",
          700: "#4B5261",
          900: "#FDFDFD",
          base: "#697488"
        },
        black: {
          50: "#F6F6F6",
          600: "#191919",
          700: "#1B242D",
          base: "#000000"
        },
        success: {
          50: "#F0FDF4",
          base: "#16A34A"
        },
        error: {
          50: "#FEF2F2",
          base: "#DC2626"
        },
        warning: {
          50: "#FEF7E8",
          base: "#F8AA1C"
        },
        blue: {
          50: "#EFF6FF",
          100: "#161D31",
          base: "#2563EB"
        },
        gurubase: {
          base: "#FF0000"
        },
        kubernetes: {
          95: "#E8EFFC",
          base: "#326CE5"
        },
        docker: {
          95: "#E6F6FE",
          base: "#066DA5"
        },
        javascript: {
          95: "#FDF9E8",
          base: "#E9CA32"
        },
        java: {
          95: "#FFF2E5",
          base: "#E76F00"
        },
        react: {
          95: "#E6F9FE",
          base: "#61DAFB"
        },
        vue: {
          95: "#ECF8F3",
          base: "#41B883"
        },
        postgre: {
          95: "#ECF3F8",
          base: "#336791"
        },
        mongoDB: {
          95: "#F1F7ED",
          base: "#6CAC48"
        },
        php: {
          95: "#F2F2F2",
          base: "#000000"
        },
        flutter: {
          95: "#E6F7FE",
          base: "#47C5FB"
        },
        kotlin: {
          95: "#FFF3E5",
          base: "#FF8901"
        },
        mysql: {
          95: "#EFF3F6",
          base: "#5D87A1"
        },
        cplus: {
          95: "#E5F3FF",
          base: "#004482"
        },
        python: {
          95: "#FFFAE5",
          base: "#F6C500"
        },
        clickhouse: {
          95: "#F2F2F2",
          base: "#000000"
        },
        prometheus: {
          95: "#FBECE9",
          base: "#DA4E31"
        },
        anteon: {
          red: "#FF4C4D",
          orange: "#FF9933",
          yellow: "#FFBF00",
          green: "#1FAD66",
          "green-alt": "#26D97F",
          cyan: "#0F8A8A",
          "cyan-alt": "#47EBEB",
          blue: "#0080FF",
          selection: "#F7A71C",
          "enterprise-purple": "#4D0099",
          "enterprise-purple-2": "#8000ff",
          "enterprise-purple-3": "#E6CCFF",
          "enterprise-purple-4": "#3C216A",
          "blue-alt": "#6EB3F7",
          "blue-2": "#58AFDF",
          "blue-2-light": "#E6F7FF",
          "react-dark-link": "#149ECA",
          "react-light-link": "#087EA4",
          "react-dark-code": "#16181D",
          "react-light-code": "#FFFFFF",
          indigo: "#3333FF",
          "indigo-alt": "#8080FF",
          purple: "#8000FF",
          "purple-alt": "#B366FF",
          pink: "#ED5EC9",
          bg: "#0A0A29",
          kdb: "#DBDBF0",
          "react-dark-orange": "#DB7D27",
          "react-dark-purple": "#8891EC",
          "react-dark-green": "#44AC99",
          "react-dark-green-alt": "#26D97F",
          "react-light-orange": "#C76A15",
          "react-light-purple": "#575FB7",
          "react-light-green": "#2B6E62",
          "react-light-green-alt": "#24A866",
          "react-light-orange-bg": "#FEF5E7",
          "react-light-purple-bg": "#F3F4FD",
          "react-light-green-bg": "#F4FBF9",
          "bg-alt": "#262640",
          "link-dark": "#6EB3F7",
          "link-light": "#0080FF",
          "landing-tile-icon-border": "#4D4DB2",
          "landing-playground-border": "#4D4DB2",
          "landing-tile-image-border": "#272762",
          "landing-stats-fallback-bg": "#242442",
          "landing-footer-bg": "#0F0F3D",
          "landing-footer-border": "#2E2E78",
          "walkthrough-button-bg": "#4D4DB2",
          "walkthrough-button-alt-bg": "#474E6B",
          "enterprise-table-alt-dark": "#1D1E30",
          "enterprise-table-alt": "#F4F8FB",
          discord: "#5865F2"
        },
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))"
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))"
        },
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))"
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))"
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))"
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))"
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))"
        },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        chart: {
          1: "hsl(var(--chart-1))",
          2: "hsl(var(--chart-2))",
          3: "hsl(var(--chart-3))",
          4: "hsl(var(--chart-4))",
          5: "hsl(var(--chart-5))"
        }
      },
      keyframes: {
        loading: {
          "0%": {
            width: "10%",
            backgroundColor: "#F0F1F3",
            opacity: "1"
          },
          "100%": {
            width: "97%",
            backgroundColor: "#F0F1F3",
            opacity: "1"
          }
        }
      },
      animation: {
        loading: "loading 4s forwards"
      },
      backgroundOpacity: {
        10: "0.1",
        20: "0.2",
        50: "0.5",
        95: "0.95"
      },
      fontFamily: {
        "jetBrains-mono": ["JetBrains Mono", ...defaultTheme.fontFamily.mono],
        "gilroy-semibold": ["var(--gilroy-semibold)", "sans-serif"],
        inter: ["var(--font-inter)", "sans-serif"]
      },
      fontSize: {
        0: ["0px", "0px"],
        base: ["1rem", "1.75rem"],
        xl: ["1.25rem", "2rem"],
        h1: ["var(--fs-h1)", { lineHeight: "var(--lh-h1)" }],
        h2: ["var(--fs-h2)", { lineHeight: "var(--lh-h2)" }],
        h3: ["var(--fs-h3)", { lineHeight: "var(--lh-h3)" }],
        h4: ["var(--fs-h4)", { lineHeight: "var(--lh-h4)" }],
        h5: ["var(--fs-h5)", { lineHeight: "var(--lh-h5)" }],
        body: ["var(--fs-body)", { lineHeight: "var(--lh-body)" }],
        body2: ["var(--fs-body-2)", { lineHeight: "var(--lh-body-2)" }],
        body3: ["var(--fs-body-3)", { lineHeight: "var(--lh-body-3)" }],
        body4: ["var(--fs-body-4)", { lineHeight: "var(--lh-body-4)" }],
        caption: ["var(--fs-caption)", { lineHeight: "var(--lh-caption)" }]
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-conic":
          "conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))"
      },
      screens: {
        "max-w-full": {
          raw: "(max-width: 100%)"
        },
        "guru-lg": {
          min: "1367px"
        },
        "guru-md": {
          max: "1366px"
        },
        "guru-sm": {
          max: "915px"
        },
        "guru-xs": {
          max: "768px"
        },
        xs: {
          max: "768px"
        }
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)"
      }
    },
    variants: {
      extend: {
        backgroundOpacity: ["active"],
        backdropFilter: ["responsive"]
      }
    }
  },
  plugins: [require("@tailwindcss/typography"), require("tailwindcss-animate")]
};
