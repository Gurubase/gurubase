import TermsOfUseClient from "@/components/TermsOfUse/TermsOfUseClient";

export async function generateMetadata({ params, searchParams }) {
  let mainOgImage =
    "https://s3.eu-central-1.amazonaws.com/anteon-strapi-cms-wuby8hpna3bdecoduzfibtrucp5x/Og_image_06c9ac418a.png";

  return {
    metadataBase: process.env.NEXT_PUBLIC_PROJECT_URL,
    title: "Terms of Use - Gurubase.io",
    description: `Search for comprehensive resources on technical topics and receive instant answers.`,
    openGraph: {
      url: process.env.NEXT_PUBLIC_PROJECT_URL + "terms-of-use",
      title: "Terms of Use - Gurubase.io",
      description: `Search for comprehensive resources on technical topics and receive instant answers.`,
      images: mainOgImage
    },
    alternates: {
      canonical: process.env.NEXT_PUBLIC_PROJECT_URL + "terms-of-use"
    }
  };
}

const Home = async () => {
  return <TermsOfUseClient />;
};

export default Home;
