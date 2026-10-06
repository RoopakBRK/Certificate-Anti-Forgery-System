import type { Config } from "tailwindcss";

const config: Config = {
    content: [
        "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
        "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
        "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            colors: {
                // Trust palette: navy base, paper surfaces, one colour per verdict
                navy: {
                    50: "#F2F5FA",
                    100: "#E3E9F3",
                    200: "#C4D0E4",
                    300: "#93A7C8",
                    400: "#5E77A3",
                    500: "#3B5482",
                    600: "#284066",
                    700: "#1B2F50",
                    800: "#122440",
                    900: "#0B1F3A",
                    950: "#07142A",
                },
                paper: {
                    DEFAULT: "#FAF8F3",
                    dark: "#F1EDE3",
                },
                verified: {
                    50: "#ECFDF5",
                    100: "#D1FAE5",
                    200: "#A7F3D0",
                    600: "#059669",
                    700: "#047857",
                    800: "#065F46",
                },
                warn: {
                    50: "#FFFBEB",
                    100: "#FEF3C7",
                    200: "#FDE68A",
                    600: "#D97706",
                    700: "#B45309",
                    800: "#92400E",
                },
                danger: {
                    50: "#FEF2F2",
                    100: "#FEE2E2",
                    200: "#FECACA",
                    600: "#DC2626",
                    700: "#B91C1C",
                    800: "#991B1B",
                },
                gold: {
                    400: "#D4B26A",
                    500: "#B8954A",
                },
            },
            fontFamily: {
                display: ["var(--font-display)", "Georgia", "serif"],
                sans: ["var(--font-sans)", "system-ui", "sans-serif"],
                mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
            },
            boxShadow: {
                card: "0 1px 2px rgba(11,31,58,0.04), 0 8px 24px -8px rgba(11,31,58,0.12)",
                lift: "0 2px 4px rgba(11,31,58,0.06), 0 24px 48px -16px rgba(11,31,58,0.25)",
            },
        },
    },
    plugins: [],
};

export default config;
