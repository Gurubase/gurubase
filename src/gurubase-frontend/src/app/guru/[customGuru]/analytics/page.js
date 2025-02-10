import { redirect } from "next/navigation";

import { getMyGurus } from "@/app/actions";
import AnalyticsPageLayout from "@/components/Analytics/AnalyticsPageLayout";

export default async function AnalyticsPage({ params, searchParams }) {
  const { customGuru } = params;
  const interval = searchParams.interval || "30d";

  const guruTypes = await getMyGurus();

  return (
    <AnalyticsPageLayout
      customGuru={customGuru}
      guruTypes={guruTypes}
      initialInterval={interval}
    />
  );
}
