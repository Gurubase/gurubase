"use client";

import { ThemeProvider } from "next-themes";

export function ThemeProviderWrapper({ children }) {
  return (
    <ThemeProvider
      disableTransitionOnChange
      enableSystem
      attribute="class"
      defaultTheme="system"
      storageKey="gurubase-theme">
      {children}
    </ThemeProvider>
  );
}
