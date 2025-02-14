import { redirect } from "next/navigation";

import { getGuruTypes, getMyGurus } from "@/app/actions";
import IntegrationContent from "@/components/Integrations/IntegrationContent";
import IntegrationPayeLayout from "@/components/Integrations/IntegrationPayeLayout";
import WebWidgetIntegrationContent from "@/components/Integrations/WebWidgetIntegrationContent";

export default async function IntegrationsPage({ params, searchParams }) {
  const { customGuru, integrationType } = params;
  const type =
    integrationType.charAt(0).toUpperCase() + integrationType.slice(1);
  const hasError = searchParams && searchParams.error === "true";

  const guruTypes = await getMyGurus();
  const currentGuru = guruTypes.find((guru) => guru.slug === customGuru);

  const selfhosted = process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted";

  // Determine which content component to use based on integration type
  const getIntegrationContent = (selfhosted) => {
    switch (integrationType) {
      case "web_widget":
        return (
          <WebWidgetIntegrationContent
            customGuru={customGuru}
            guruData={currentGuru}
          />
        );
      case "slack":
      case "discord":
        return (
          <IntegrationContent
            customGuru={customGuru}
            error={hasError}
            selfhosted={selfhosted}
            type={integrationType}
          />
        );
      default:
        return null;
    }
  };

  const content = getIntegrationContent(selfhosted);

  if (!content) {
    redirect("/not-found");
  }

  return (
    <IntegrationPayeLayout
      content={content}
      customGuru={customGuru}
      error={hasError}
      guruTypes={guruTypes}
      type={type}
    />
  );
}
