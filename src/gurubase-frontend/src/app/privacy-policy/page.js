import PrivacyPolicyClient from "@/components/PrivacyPolicy/PrivacyPolicyClient";

export async function generateMetadata({ params, searchParams }) {
  let mainOgImage =
    "https://s3.eu-central-1.amazonaws.com/anteon-strapi-cms-wuby8hpna3bdecoduzfibtrucp5x/Og_image_06c9ac418a.png";

  return {
    metadataBase: process.env.NEXT_PUBLIC_PROJECT_URL,
    title: "Privacy Policy - Gurubase.io",
    description: `Search for comprehensive resources on technical topics and receive instant answers.`,
    openGraph: {
      url: process.env.NEXT_PUBLIC_PROJECT_URL + "privacy-policy",
      title: "Privacy Policy - Gurubase.io",
      description: `Search for comprehensive resources on technical topics and receive instant answers.`,
      images: mainOgImage
    },
    alternates: {
      canonical: process.env.NEXT_PUBLIC_PROJECT_URL + "privacy-policy"
    }
  };
}

const Home = async () => {
  return <PrivacyPolicyClient />;
};

export default Home;
