import { redirect } from "next/navigation";

import { getMyGurus } from "@/app/actions";
import AnalyticsPageLayout from "@/components/Analytics/AnalyticsPageLayout";

export default async function AnalyticsPage({ params, searchParams }) {
  const { customGuru } = params;
  const hasError = searchParams && searchParams.error === "true";

  const guruTypes = await getMyGurus();
  const currentGuru = guruTypes.find((guru) => guru.slug === customGuru);

  const selfhosted = process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted";

  if (selfhosted) {
    redirect("/not-found");
  }

  return <AnalyticsPageLayout customGuru={customGuru} guruTypes={guruTypes} />;
}
