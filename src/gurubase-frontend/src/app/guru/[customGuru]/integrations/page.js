import { getMyGurus } from "@/app/actions";
import IntegrationPayeLayout from "@/components/Integrations/IntegrationPayeLayout";
import IntegrationTypesList from "@/components/Integrations/IntegrationTypesList";

export default async function IntegrationsPage({ params }) {
  const { customGuru } = params;
  const guruTypes = await getMyGurus();

  return (
    <IntegrationPayeLayout
      content={<IntegrationTypesList customGuru={customGuru} />}
      customGuru={customGuru}
      guruTypes={guruTypes}
    />
  );
}
