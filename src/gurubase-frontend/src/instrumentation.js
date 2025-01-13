export async function register() {
  if (
    process.env.NEXT_RUNTIME === "nodejs" &&
    process.env.NEXT_PUBLIC_NODE_ENV === "production"
  ) {
    await import("../sentry.server.config");
  }

  if (
    process.env.NEXT_RUNTIME === "edge" &&
    process.env.NEXT_PUBLIC_NODE_ENV === "production"
  ) {
    await import("../sentry.edge.config");
  }
}
