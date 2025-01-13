import { handleAuth } from "@auth0/nextjs-auth0";
import { redirect } from "next/navigation";

export const GET =
  process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted"
    ? () => redirect("/not-found")
    : handleAuth();
