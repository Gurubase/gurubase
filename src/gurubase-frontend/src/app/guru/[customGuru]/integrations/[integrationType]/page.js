import { redirect } from "next/navigation";

import { getMyGuru } from "@/app/actions";
import IntegrationContent from "@/components/Integrations/IntegrationContent";
import IntegrationPayeLayout from "@/components/Integrations/IntegrationPayeLayout";
import WebWidgetIntegrationContent from "@/components/Integrations/WebWidgetIntegrationContent";

// Check if beta features are enabled via environment variable
const isBetaFeaturesEnabled = process.env.NEXT_PUBLIC_BETA_FEAT_ON === "true";

export default async function IntegrationsPage({ params, searchParams }) {
  const { customGuru, integrationType } = params;

  const guruData = await getMyGuru(customGuru);

  const selfhosted = process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted";

  // Determine which content component to use based on integration type
  const getIntegrationContent = (selfhosted) => {
    switch (integrationType) {
      case "web_widget":
        return <WebWidgetIntegrationContent guruData={guruData} />;

      case "jira":
      case "zendesk":
      case "confluence":
        if (!isBetaFeaturesEnabled) {
          return null; // If beta features are off, treat as not found
        }
      // If beta features are on, fall through to render IntegrationContent
      /* falls through */
      case "slack":
      case "discord":
      case "github":
        return (
          <IntegrationContent
            guruData={guruData}
            error={searchParams?.error}
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

  return <IntegrationPayeLayout content={content} guruData={guruData} />;
}
