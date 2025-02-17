import { revalidateTag } from "next/cache";
import { notFound, redirect } from "next/navigation";

import { getMyGuru } from "@/app/actions";
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
  const guruData = await getMyGuru(customGuru);

  // Add null check for guruTypes
  if (guruData.error) {
    notFound();
  }

  // Determine if the guru is still processing
  const isProcessing = guruData.ready === false;

  return <NewGuruClient guruData={guruData} isProcessing={isProcessing} />;
};

export default CustomGuru;
