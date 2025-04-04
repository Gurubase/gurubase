import { getUserSession } from "@/app/actions";
import { redirect } from "next/navigation";

import { getApiKeys } from "@/app/actions";
import APIKeysMainPage from "@/components/APIKeysMainPage";

const ApiKeysPage = async () => {
  let session = null;

  if (process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted") {
    session = null;
  } else {
    session = await getUserSession();
    if (!session?.user) {
      redirect("/not-found");
    }
  }

  return (
    <div>
      <APIKeysMainPage />
    </div>
  );
};

export default ApiKeysPage;
