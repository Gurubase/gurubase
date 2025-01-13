import { getSession } from "@auth0/nextjs-auth0";
import { redirect } from "next/navigation";

import { getGuruTypes } from "@/app/actions";
import BingeHistoryMainPage from "@/components/BingeHistoryMainPage";

const Home = async () => {
  // get guru types
  const allGuruTypes = await getGuruTypes();

  // Filter guru types to include only those with ready state true
  // const readyGuruTypes = Array.isArray(allGuruTypes)
  //   ? allGuruTypes.filter((guruType) => guruType.ready === true)
  //   : [];

  // process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted";
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
      <BingeHistoryMainPage guruTypes={allGuruTypes} />
    </div>
  );
};

export default Home;
