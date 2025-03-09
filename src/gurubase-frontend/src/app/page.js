// invalidate every 1 minutes
import { getGuruTypes } from "@/app/actions";
import HomePageClient from "@/components/HomePageClient";

export const revalidate = 60;
export const dynamic = "force-dynamic";
const Home = async () => {
  // get guru types
  const allGuruTypes = await getGuruTypes();

  const readyGuruTypes = Array.isArray(allGuruTypes)
    ? // ? allGuruTypes.filter((guruType) => guruType.ready === true)
    allGuruTypes
    : [];

  return <HomePageClient allGuruTypes={readyGuruTypes} />;
};

export default Home;
