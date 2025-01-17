// import { getGuruPromptMap } from "@/components/Header/utils";
import { redirect } from "next/navigation";

import {
  fetchDefaultQuestion,
  getGuruType,
  getGurutypeResources,
  getGuruTypes
} from "@/app/actions";
import GuruTypeClient from "@/components/GuruTypeClient";
import GuruTypeInitializer from "@/components/GuruTypeInitializer";

export async function generateMetadata({ params, searchParams }) {
  const { guruType, slug } = params;
  let mainOgImage =
    "https://s3.eu-central-1.amazonaws.com/anteon-strapi-cms-wuby8hpna3bdecoduzfibtrucp5x/Og_image_06c9ac418a.png";

  const data = await getGuruType(guruType);

  // Create OG image URL based on environment
  let guruTypeOgImage;
  const env = process.env.NEXT_PUBLIC_NODE_ENV;

  if (env === "development" || env === "staging" || env === "production") {
    const envFolder = env === "development" ? "dev" : env;

    guruTypeOgImage = `https://storage.googleapis.com/gurubase-og-images/${envFolder}/custom-base-templates/${guruType}.jpg`;
  }

  if (guruType && !slug) {
    const guruName = data?.name || guruType;
    const canonicalUrl = `${process.env.NEXT_PUBLIC_PROJECT_URL}g/${guruType}`;

    return {
      title: `Your Shortcut Search for ${guruName} | Gurubase`,
      description: `Search for anything related to ${guruName} and receive instant answers.`,
      openGraph: {
        title: `Your Shortcut Search for ${guruName} | Gurubase`,
        description: `Search for anything related to ${guruName} and receive instant answers.`,
        images: guruTypeOgImage || mainOgImage,
        url: canonicalUrl
      },
      alternates: {
        canonical: canonicalUrl
      }
    };
  }
}

const Home = async (context) => {
  const { params } = context;
  const { guruType } = params;

  // get guru types

  const allGuruTypes = await getGuruTypes();

  // Filter guru types to include only those with ready state true
  // const readyGuruTypes = allGuruTypes.filter(
  //   (guruType) => guruType.ready === true
  // );

  // if guruType is not found in allGuruTypes, return 404
  if (!allGuruTypes?.find((guru) => guru.slug === guruType)) {
    return redirect(`/not-found`);
  }

  const readyGuruTypes = allGuruTypes;

  // get default questions
  let defaultQuestions = [];

  try {
    const data = await fetchDefaultQuestion(guruType);

    if (data && data.length > 3) {
      defaultQuestions = data.slice(0, 3);
    } else {
      defaultQuestions = data ? data : [];
    }
  } catch (error) {
    // console.error("Error occurred in default questions get:", error);
  }

  // get guruType resources
  let resources = [];

  try {
    const data = await getGurutypeResources(guruType);

    resources = data;
  } catch (error) {
    // console.error("Error occurred in guru Type resources get:", error);
  }

  return (
    <>
      <GuruTypeInitializer />
      <GuruTypeClient
        allGuruTypes={readyGuruTypes}
        defaultQuestions={defaultQuestions}
        guruType={guruType}
        resources={resources?.resources}
      />
    </>
  );
};

export default Home;
