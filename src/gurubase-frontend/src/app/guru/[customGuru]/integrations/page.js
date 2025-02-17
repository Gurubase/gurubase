import { getMyGuru } from "@/app/actions";
import IntegrationPayeLayout from "@/components/Integrations/IntegrationPayeLayout";
import IntegrationTypesList from "@/components/Integrations/IntegrationTypesList";

export default async function IntegrationsPage({ params }) {
  const { customGuru } = params;
  const customGuruData = await getMyGuru(customGuru);

  return (
    <IntegrationPayeLayout
      content={<IntegrationTypesList guruData={customGuruData} />}
      guruData={customGuruData}
    />
  );
}
