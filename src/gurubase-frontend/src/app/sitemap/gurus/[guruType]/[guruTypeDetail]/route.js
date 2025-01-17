import { getSitemapData } from "@/app/actions";

// Important source code https://github.com/vercel/next.js/discussions/61025

export async function GET(request, context) {
  // Fetch the total number of products and calculate the number of sitemaps needed
  // get the guruType parameter from the url
  const { guruType, guruTypeDetail } = context.params;

  let slug = "";

  if (guruTypeDetail === "sitemap_index.xml") {
    slug = `${guruType}/sitemap.xml`;
  } else {
    slug = `${guruType}/${guruTypeDetail}`;
  }

  const sitemapData = await getSitemapData(slug);

  return new Response(sitemapData, {
    headers: { "Content-Type": "text/xml" }
  });
}
