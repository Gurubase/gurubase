import { withSentryConfig } from "@sentry/nextjs";
import MonacoWebpackPlugin from "monaco-editor-webpack-plugin";

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  env: {
    ...(process.env.NEXT_PUBLIC_NODE_ENV !== "selfhosted"
      ? {
        AUTH0_SECRET: process.env.AUTH0_SECRET,
        AUTH0_BASE_URL: process.env.AUTH0_BASE_URL,
        AUTH0_ISSUER_BASE_URL: process.env.AUTH0_ISSUER_BASE_URL,
        AUTH0_CLIENT_ID: process.env.AUTH0_CLIENT_ID,
        AUTH0_CLIENT_SECRET: process.env.AUTH0_CLIENT_SECRET,
        AUTH0_AUDIENCE: process.env.AUTH0_AUDIENCE,
        AUTH0_ALGORITHMS: process.env.AUTH0_ALGORITHMS,
        AUTH0_SCOPE: "openid profile email offline_access"
      }
      : {})
  },
  eslint: {
    ignoreDuringBuilds: true
  },
  images: {
    dangerouslyAllowSVG: true,
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**"
      },
      {
        protocol: "http",
        hostname: "**"
      }
    ]
  },
  experimental: {
    instrumentationHook:
      process.env.NEXT_PUBLIC_INSTRUMENTATION_HOOK === "false" ? false : true,
    serverActions: {
      allowedOrigins:
        process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted"
          ? ["*"]
          : ["kubernetesguru-backend-api.getanteon.com", "*.getanteon.com"],
      bodySizeLimit: "5mb"
    },
    optimizeCss: true
  },
  webpack: (config, { isServer }) => {
    if (!isServer) {
      config.plugins.push(
        new MonacoWebpackPlugin({
          languages: ["javascript", "typescript", "html", "css", "json"],
          filename: "static/[name].worker.js"
        })
      );
    }

    return config;
  },
  async headers() {
    return [
      {
        // Match all paths
        source: "/:path*",
        headers: [
          // 1. Content Security Policy (CSP)
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' 'unsafe-eval' *.googleapis.com *.gstatic.com *.google.com *.googletagmanager.com *.cloudflare.com *.cloudflareinsights.com *.jsdelivr.net *.posthog.com *.i.posthog.com us-assets.i.posthog.com *.hotjar.com *.mixpanel.com",
              "worker-src 'self' blob:",
              "style-src 'self' 'unsafe-inline' *.googleapis.com *.jsdelivr.net",
              process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted"
                ? "img-src 'self' data: blob: *"
                : "img-src 'self' data: blob: *.googleusercontent.com *.google-analytics.com *.googletagmanager.com *.hotjar.com *.jsdelivr.net *.googleapis.com *.githubusercontent.com *.amazonaws.com",
              "font-src 'self' data: *.gstatic.com *.jsdelivr.net",
              "frame-src 'self' *.auth0.com *.hotjar.com",
              process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted"
                ? "connect-src 'self' *"
                : "connect-src 'self' localhost:* 127.0.0.1:* gurubase-backend:* *.getanteon.com *.gurubase.ai *.amazonaws.com *.jsdelivr.net *.auth0.com *.iconify.design *.unisvg.com *.simplesvg.com *.hotjar.com *.hotjar.io wss://*.hotjar.com *.mixpanel.com *.google-analytics.com *.analytics.google.com *.sentry.io *.ingest.sentry.io *.gurubase.io",
              "form-action 'self' *.auth0.com",
              "object-src 'none'",
              "base-uri 'self'",
              "frame-ancestors 'none'",
              ...(process.env.NEXT_PUBLIC_NODE_ENV !== "selfhosted"
                ? ["upgrade-insecure-requests"]
                : [])
            ].join("; ")
          },
          // 2. X-Frame-Options
          {
            key: "X-Frame-Options",
            value: "DENY"
          },
          // 3. HTTP Strict Transport Security (HSTS)
          {
            key: "Strict-Transport-Security",
            value: "max-age=31536000; includeSubDomains; preload"
          },
          // 4. X-XSS-Protection
          {
            key: "X-XSS-Protection",
            value: "1; mode=block"
          },
          // 5. X-Content-Type-Options
          {
            key: "X-Content-Type-Options",
            value: "nosniff"
          },
          // 6. Referrer-Policy
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin"
          },
          // 7. Permissions-Policy
          {
            key: "Permissions-Policy",
            value: [
              "accelerometer=()",
              "camera=()",
              "geolocation=()",
              "gyroscope=()",
              "magnetometer=()",
              "microphone=()",
              "payment=()",
              "usb=()"
            ].join(", ")
          },
          // 8. Remove or hide server information
          {
            key: "Server",
            value: ""
          }
        ]
      }
    ];
  },
  swcMinify: true,
  compiler: {
    removeConsole: process.env.NODE_ENV === "production"
  }
};

export default withSentryConfig(nextConfig, {
  // For all available options, see:
  // https://github.com/getsentry/sentry-webpack-plugin#options

  org: process.env.NEXT_PUBLIC_SENTRY_ORG,
  project: process.env.NEXT_PUBLIC_SENTRY_PROJECT,

  // Only print logs for uploading source maps in CI
  silent: !process.env.CI,

  // For all available options, see:
  // https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/

  // Upload a larger set of source maps for prettier stack traces (increases build time)
  widenClientFileUpload: false,

  // Route browser requests to Sentry through a Next.js rewrite to circumvent ad-blockers.
  // This can increase your server load as well as your hosting bill.
  // Note: Check that the configured route will not match with your Next.js middleware, otherwise reporting of client-
  // side errors will fail.
  // tunnelRoute: "/monitoring",

  // Hides source maps from generated client bundles
  hideSourceMaps: true,

  // Automatically tree-shake Sentry logger statements to reduce bundle size
  disableLogger: true,

  // Enables automatic instrumentation of Vercel Cron Monitors. (Does not yet work with App Router route handlers.)
  // See the following for more information:
  // https://docs.sentry.io/product/crons/
  // https://vercel.com/docs/cron-jobs
  automaticVercelMonitors: false
});
