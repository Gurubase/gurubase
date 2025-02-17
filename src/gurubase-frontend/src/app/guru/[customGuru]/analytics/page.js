import { getMyGuru } from "@/app/actions";
import AnalyticsPageLayout from "@/components/Analytics/AnalyticsPageLayout";

export default async function AnalyticsPage({ params, searchParams }) {
  const { customGuru } = params;
  const interval = searchParams.interval || "30d";

  const guruData = await getMyGuru(customGuru);

  return <AnalyticsPageLayout guruData={guruData} initialInterval={interval} />;
}
