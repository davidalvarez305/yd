import plugin from "tailwindcss/plugin";
import defaultTheme from "tailwindcss/defaultTheme";
import colors from "tailwindcss/colors";

import aspectRatio from "@tailwindcss/aspect-ratio";
import forms from "@tailwindcss/forms";
import typography from "@tailwindcss/typography";

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "../website/**/templates/**/*.html",
    "../website/**/*.py",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        primary: {
            DEFAULT: '#9A2167',
            50: '#E68CC0',
            100: '#E37BB7',
            200: '#DC5AA5',
            300: '#D43893',
            400: '#BC287D',
            500: '#9A2167',
            600: '#6C1748',
            700: '#3E0D29',
            800: '#0F030A',
            900: '#000000',
            950: '#000000'
				},
        secondary: {
            DEFAULT: '#F69223',
            50: '#FDE9D3',
            100: '#FCE0C0',
            200: '#FBCC99',
            300: '#F9B971',
            400: '#F8A54A',
            500: '#F69223',
            600: '#D87609',
            700: '#A25807',
            800: '#6C3B04',
            900: '#361E02',
            950: '#1B0F01'
				},
        tertiary: {
            DEFAULT: '#ED3788',
            50: '#FCDFEC',
            100: '#FACDE1',
            200: '#F7A7CB',
            300: '#F482B5',
            400: '#F05C9E',
            500: '#ED3788',
            600: '#D8136B',
            700: '#A50F52',
            800: '#710A38',
            900: '#3E061F',
            950: '#240312'
				},
        cta: {
          DEFAULT: '#FFDD34',
            50: '#FFDD34',
            100: '#FFDD34',
            200: '#FFDD34',
            300: '#FFDD34',
            400: '#FFDD34',
            500: '#FFDD34',
            600: '#FFDD34',
            700: '#FFDD34',
            800: '#FFDD34',
            900: '#FFDD34',
            950: '#FFDD34'
        }
      },
      fontFamily: {
        sans: ["Inter", ...defaultTheme.fontFamily.sans],
      },
      maxWidth: {
        "8xl": "90rem",
        "9xl": "105rem",
        "10xl": "120rem",
      },
      zIndex: {
        1: 1,
        60: 60,
        70: 70,
        80: 80,
        90: 90,
        100: 100,
      },
      keyframes: {
        "spin-slow": {
          "100%": {
            transform: "rotate(-360deg)",
          },
        },
      },
      animation: {
        "spin-slow": "spin-slow 8s linear infinite",
      },
      typography: {
        DEFAULT: {
          css: {
            a: {
              textDecoration: "none",
              "&:hover": {
                opacity: ".75",
              },
            },
            img: {
              borderRadius: defaultTheme.borderRadius.lg,
            },
          },
        },
      },
    },
  },
  plugins: [
    aspectRatio,
    forms,
    typography,
    plugin(function ({ addUtilities }) {
      const utilFormSwitch = {
        ".form-switch": {
          border: "transparent",
          "background-color": colors.gray[300],
          "background-image":
            "url(\"data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='-4 -4 8 8'%3e%3ccircle r='3' fill='%23fff'/%3e%3c/svg%3e\")",
          "background-position": "left center",
          "background-repeat": "no-repeat",
          "background-size": "contain !important",
          "vertical-align": "top",
          "&:checked": {
            border: "transparent",
            "background-color": "currentColor",
            "background-image":
              "url(\"data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='-4 -4 8 8'%3e%3ccircle r='3' fill='%23fff'/%3e%3c/svg%3e\")",
            "background-position": "right center",
          },
          "&:disabled, &:disabled + label": {
            opacity: ".5",
            cursor: "not-allowed",
          },
        },
      };

      addUtilities(utilFormSwitch);
    }),
  ],
};