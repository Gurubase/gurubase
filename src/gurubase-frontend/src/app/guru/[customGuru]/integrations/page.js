import { getGuruTypes } from "@/app/actions";
import IntegrationPayeLayout from "@/components/Integrations/IntegrationPayeLayout";
import IntegrationTypesList from "@/components/Integrations/IntegrationTypesList";

export default async function IntegrationsPage({ params }) {
  const { customGuru } = params;
  const guruTypes = await getGuruTypes();

  return (
    <IntegrationPayeLayout
      content={<IntegrationTypesList customGuru={customGuru} />}
      customGuru={customGuru}
      guruTypes={guruTypes}
    />
  );
}
