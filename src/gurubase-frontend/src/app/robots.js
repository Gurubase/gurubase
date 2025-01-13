export default function robots() {
  if (process.env.NEXT_PUBLIC_NODE_ENV === "production") {
    return {
      rules: [
        {
          userAgent: "*",
          allow: ["/", "/g/*"],
          disallow: [
            "/_next/*",
            "/api/*",
            "/monitoring",
            "/*?*",
            "/*.js$",
            "/*.css$",
            "/static/*"
          ]
        }
      ],
      sitemap: `${process.env.NEXT_PUBLIC_PROJECT_URL}sitemap/sitemap_index.xml`
    };
  } else {
    return {
      rules: {
        userAgent: "*",
        disallow: "/"
      }
    };
  }
}
