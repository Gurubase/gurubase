import clsx from "clsx";
import Image from "next/image";

import GurubaseLogo from "@/assets/images/guru-base.svg";
import SocialMediaHeader from "@/components/Header/SocialMediaHeader";
import { Link } from "@/components/Link";
import useIsSmallScreen from "@/utils/hooks/useIsSmallScreen";

import NotificationCard from "./NotificationCard/NotificationCard";

export default function Footer({ sidebarExists = false }) {
  const isSmallScreen = useIsSmallScreen();

  // Don't render footer on mobile screens
  if (isSmallScreen) {
    return null;
  }

  return (
    <main className="flex justify-center items-center text-xs bg-white dark:bg-[rgb(var(--background))] border-t border-solid border-neutral-200 dark:border-[rgb(var(--border))] w-full py-3 guru-sm:mb-0 guru-sm:pb-2 z-40 guru-md:z-auto">
      <section
        className={clsx(
          "flex flex-col justify-center border-0 border-solid border-neutral-200 flex-grow mx-6 guru-sm:mx-5",
          sidebarExists
            ? "max-w-[1440px]"
            : "guru-md:max-w-[870px] guru-lg:max-w-[1180px]"
        )}>
        <article className="flex gap-5 items-start flex-wrap flex-col lg:flex-row">
          <section className="flex flex-row justify-between guru-sm:justify-between guru-sm:flex-row flex-1 self-stretch">
            <Image
              alt="Gurubase Logo"
              className="max-w-full aspect-[5] w-[119px] guru-sm:hidden dark:invert dark:brightness-200 dark:contrast-200"
              height={0}
              loading="lazy"
              src={GurubaseLogo}
              style={{ width: "120px", height: "auto" }}
              width={0}
            />
            <SocialMediaHeader isMobile={true} />

            <p className="text-gray-400 dark:text-gray-300 guru-sm:hidden italic text-base font-medium">
              AI-powered Q&A assistants for any topic
            </p>
            <div className="flex justify-end items-center guru-sm:gap-2 gap-4">
              <Link href="/privacy-policy" prefetch={false}>
                <span className="text-gray-400 dark:text-gray-300 hover:text-gray-600 dark:hover:text-gray-100 transition-colors">
                  Privacy Policy
                </span>
              </Link>
              <Link href="/terms-of-use" prefetch={false}>
                <span className="text-gray-400 dark:text-gray-300 hover:text-gray-600 dark:hover:text-gray-100 transition-colors">
                  Terms of Use
                </span>
              </Link>
            </div>
          </section>
        </article>
      </section>
      <NotificationCard />
    </main>
  );
}
