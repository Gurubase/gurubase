import { getUserSession } from "@/app/actions";
import { redirect } from "next/navigation";

import SettingsMainPage from "@/components/SettingsMainPage";

const SettingsPage = async () => {
  // Only allow access in self-hosted mode
  if (process.env.NEXT_PUBLIC_NODE_ENV !== "selfhosted") {
    redirect("/not-found");
  }

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
      <SettingsMainPage />
    </div>
  );
};

export default SettingsPage;
