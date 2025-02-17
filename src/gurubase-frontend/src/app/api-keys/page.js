import { getSession } from "@auth0/nextjs-auth0";
import { redirect } from "next/navigation";

import { getApiKeys } from "@/app/actions";
import APIKeysMainPage from "@/components/APIKeysMainPage";

const ApiKeysPage = async () => {
  let session = null;

  if (process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted") {
    session = null;
  } else {
    session = await getSession();
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
