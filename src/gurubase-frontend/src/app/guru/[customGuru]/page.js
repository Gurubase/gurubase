import { revalidateTag } from "next/cache";
import { notFound, redirect } from "next/navigation";

import { getGuruDataSources, getMyGurus } from "@/app/actions";
import { NewGuruClient } from "@/components/NewGuruClient";

export const viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false
};
// add no index meta tag
export const metadata = {
  robots: {
    index: false,
    follow: false
  }
};

const CustomGuru = async ({ params }) => {
  const { customGuru } = params;

  // Revalidate guru types cache when accessing the page
  revalidateTag("my-guru-types");

  // Fetch guru types and data sources
  const guruTypes = await getMyGurus();

  // Add null check for guruTypes
  if (guruTypes.error) {
    notFound();
  }
  const guru = guruTypes?.find(
    (guru) => guru.slug.toLowerCase() === customGuru.toLowerCase()
  );

  if (!guru) {
    notFound();
  }
  const dataSources = await getGuruDataSources(customGuru);

  // Redirect if unauthorized (dataSources is null)
  if (!dataSources) {
    redirect("/not-found");
  }

  // Determine if the guru is still processing
  const isProcessing = guru.ready === false;

  return (
    <NewGuruClient
      customGuru={customGuru}
      dataSources={dataSources}
      guruTypes={guruTypes}
      isProcessing={isProcessing}
    />
  );
};

export default CustomGuru;
