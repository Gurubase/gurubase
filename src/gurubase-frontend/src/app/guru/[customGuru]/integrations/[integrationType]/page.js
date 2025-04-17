import { redirect } from "next/navigation";

import { getMyGuru } from "@/app/actions";
import IntegrationContent from "@/components/Integrations/IntegrationContent";
import IntegrationPayeLayout from "@/components/Integrations/IntegrationPayeLayout";
import WebWidgetIntegrationContent from "@/components/Integrations/WebWidgetIntegrationContent";

export default async function IntegrationsPage({ params, searchParams }) {
  const { customGuru, integrationType } = params;

  const guruData = await getMyGuru(customGuru);

  const selfhosted = process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted";

  // Determine which content component to use based on integration type
  const getIntegrationContent = (selfhosted) => {
    switch (integrationType) {
      case "web_widget":
        return <WebWidgetIntegrationContent guruData={guruData} />;
      case "slack":
      case "discord":
      case "jira":
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
