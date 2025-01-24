import IntegrationPayeLayout from "@/components/Integrations/IntegrationPayeLayout";

export default function IntegrationsPage({ params, searchParams }) {
  const { customGuru, integrationType } = params;
  const type =
    integrationType.charAt(0).toUpperCase() + integrationType.slice(1);
  const hasError = searchParams && searchParams.error === "true";

  return (
    <IntegrationPayeLayout
      customGuru={customGuru}
      error={hasError}
      type={type}
    />
  );
}
