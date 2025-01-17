import { getSitemapData } from "@/app/actions";

// Important source code https://github.com/vercel/next.js/discussions/61025

export async function GET(request, context) {
  // Fetch the total number of products and calculate the number of sitemaps needed
  const { mainSitemap } = context.params;

  let slug = "";

  if (mainSitemap === "sitemap_index.xml") {
    slug = "sitemap.xml";
  } else {
    slug = `${"sitemap/" + mainSitemap}`;
  }

  const sitemapData = await getSitemapData(slug);

  return new Response(sitemapData, {
    headers: { "Content-Type": "text/xml" }
  });
}
