import { NewGuruClient } from "@/components/NewGuruClient";

export const viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false
};
// add no index meta tag
export const metadata = {
  robots: {
    index: false,
    follow: false
  }
};
const NewGuru = async () => {
  return <NewGuruClient />;
};
export default NewGuru;
