import { MyGurusClient } from "@/components/MyGurus";

export const metadata = {
  title: "My Gurus - Gurubase",
  description: "View and manage your personal guru collection"
};

const MyGurusPage = async () => {
  return <MyGurusClient />;
};

export default MyGurusPage; 