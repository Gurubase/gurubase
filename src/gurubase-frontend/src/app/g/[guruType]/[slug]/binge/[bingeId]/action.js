"use server";

export async function getSitemapData(slug) {

  const res = await fetch(
    `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/${slug}`,
    {
      next: { revalidate: 1 }
    }
  );

  const data = await res.text();

  return data;
}
