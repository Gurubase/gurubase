import "./globals.css";

import { UserProvider } from "@auth0/nextjs-auth0/client";
import { GoogleAnalytics } from "@next/third-parties/google";
import dynamic from "next/dynamic";
import { Inter } from "next/font/google";
import localFont from "next/font/local";
import Script from "next/script";
import { PublicEnvScript } from "next-runtime-env";

import StoreProvider from "@/app/StoreProvider";
import { Toaster } from "@/components/ui/Sonner";

import { CSPostHogProvider } from "./providers";

// Dynamically import non-critical components
const PageTransition = dynamic(
  () => import("@/components/PageTransition").then((mod) => mod.PageTransition),
  {
    ssr: false
  }
);

// Optimize font loading
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
  preload: true,
  fallback: ["system-ui", "arial"]
});

const gilroy = localFont({
  src: "./fonts/gilroy-semibold.ttf",
  display: "swap",
  variable: "--gilroy-semibold",
  preload: true,
  weight: "400",
  style: "normal",
  fallback: ["system-ui", "arial"]
});

export const runtime = process.env.NEXT_PUBLIC_RUNTIME || "edge";

export async function generateMetadata() {
  let mainOgImage =
    "https://s3.eu-central-1.amazonaws.com/anteon-strapi-cms-wuby8hpna3bdecoduzfibtrucp5x/Og_image_06c9ac418a.png";

  return {
    metadataBase: process.env.NEXT_PUBLIC_PROJECT_URL,
    title: "AI-powered Q&A assistants for any topic",
    description: `Search for comprehensive resources on technical topics and receive instant answers.`,
    openGraph: {
      url: process.env.NEXT_PUBLIC_PROJECT_URL,
      title: "AI-powered Q&A assistants for any topic",
      description: `Search for comprehensive resources on technical topics and receive instant answers.`,
      images: mainOgImage
    },
    alternates: {
      canonical: process.env.NEXT_PUBLIC_PROJECT_URL
    }
  };
}

export default function RootLayout({ children }) {
  const isSelfHosted = process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted";

  const content = (
    <html className={`${inter.variable} ${gilroy.variable}`} lang="en">
      <head>
        <PublicEnvScript />
        <meta content="yes" name="apple-mobile-web-app-capable" />
        <meta content="default" name="apple-mobile-web-app-status-bar-style" />
        <meta content="yes" name="mobile-web-app-capable" />
      </head>
      <body className={`${inter.className} overflow-x-hidden`}>
        <div className="flex min-h-screen flex-col">
          <PageTransition />
          {children}
          <Toaster />
          {process.env.NEXT_PUBLIC_NODE_ENV === "production" && (
            <>
              <GoogleAnalytics gaId="G-SF3K4F9EQ6" strategy="lazyOnload" />
              <Script
                dangerouslySetInnerHTML={{
                  __html: `
                    (function(h,o,t,j,a,r){
                      h.hj=h.hj||function(){(h.hj.q=h.hj.q||[]).push(arguments)};
                      h._hjSettings={hjid:5125159,hjsv:6};
                      a=o.getElementsByTagName('head')[0];
                      r=o.createElement('script');r.async=1;
                      r.src=t+h._hjSettings.hjid+j+h._hjSettings.hjsv;
                      a.appendChild(r);
                  })(window,document,'https://static.hotjar.com/c/hotjar-','.js?sv=');
                `
                }}
                id="HotjarIntegration"
                strategy="lazyOnload"
              />
            </>
          )}
        </div>
      </body>
    </html>
  );

  const wrappedContent = isSelfHosted ? (
    <CSPostHogProvider>{content}</CSPostHogProvider>
  ) : (
    <UserProvider>{content}</UserProvider>
  );

  return <StoreProvider>{wrappedContent}</StoreProvider>;
}
