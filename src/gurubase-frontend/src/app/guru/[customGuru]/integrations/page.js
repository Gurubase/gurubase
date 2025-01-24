import { getGuruTypes } from "@/app/actions";
import IntegrationPayeLayout from "@/components/Integrations/IntegrationPayeLayout";

export default async function IntegrationsPage({ params, searchParams }) {
  const { customGuru } = params;
  const integrationType = "slack";
  const type =
    integrationType.charAt(0).toUpperCase() + integrationType.slice(1);
  const hasError = searchParams && searchParams.error === "true";

  const guruTypes = await getGuruTypes();

  return (
    <IntegrationPayeLayout
      customGuru={customGuru}
      error={hasError}
      guruTypes={guruTypes}
      type={type}
    />
  );
}
