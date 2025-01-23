import IntegrationPayeLayout from "@/components/Integrations/IntegrationPayeLayout";

export default function IntegrationsPage({ params }) {
  const { customGuru, integrationType } = params;
  const type =
    integrationType.charAt(0).toUpperCase() + integrationType.slice(1);

  return <IntegrationPayeLayout customGuru={customGuru} type={type} />;
}
