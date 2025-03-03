import { Icon } from "@iconify/react";
import { usePathname } from "next/navigation";
import { useEffect } from "react";

import GuruBaseLogo from "@/components/GuruBaseLogo";
import { Link } from "@/components/Link";
import { Dialog, DialogContent } from "@/components/ui/dialog";

import { getNavigationItems } from "./navigationConfig";

const MobileSidebar = ({ isOpen, onClose, user }) => {
  const pathname = usePathname();

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }

    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  const isSelfHosted = process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted";

  const renderNavigationItem = (item) => (
    <div key={item.id} className="w-full">
      <Link
        className="flex items-center gap-2 py-3 rounded-lg transition-all duration-200
          hover:bg-[#F5F5F5] dark:hover:bg-gray-800 hover:pl-1 active:bg-[#EAEAEA] dark:active:bg-gray-700"
        href={item.href}
        prefetch={false}
        onClick={onClose}>
        <Icon className={`w-5 h-5 text-[${item.iconColor}]`} icon={item.icon} />
        <span className={`text-sm text-[${item.textColor}] dark:text-gray-200`}>
          {item.label}
        </span>
      </Link>
    </div>
  );

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent
        className="fixed left-0 top-0 h-full w-[240px] p-0 border-r border-[#E2E2E2] dark:border-[rgb(var(--border))] bg-white dark:bg-[rgb(var(--background))] shadow-lg 
        data-[state=open]:slide-in-from-left data-[state=closed]:slide-out-to-left
        transition-all duration-300 ease-in-out touch-pan-x
        focus:outline-none focus-visible:outline-none focus:ring-0 focus-visible:ring-0">
        <div className="flex flex-col h-full pt-[78px] pb-12 px-5">
          {/* Logo */}
          <div className="flex items-center w-full mb-8">
            <Link
              className="cursor-pointer"
              href="/"
              prefetch={false}
              onClick={onClose}>
              <GuruBaseLogo />
            </Link>
          </div>

          {/* Content Container */}
          <div className="flex-1 w-full overflow-y-auto space-y-6">
            {user ? (
              <>
                {/* User Profile Section */}
                <div className="pb-6 border-b border-[#E2E2E2] dark:border-[rgb(var(--border))]">
                  <div className="flex flex-col">
                    <p className="text-base font-semibold text-[#191919] dark:text-[rgb(var(--foreground))] mb-1">
                      {user.name}
                    </p>
                    <p className="text-sm text-[#6D6D6D] dark:text-gray-400">
                      {user.email}
                    </p>
                  </div>
                </div>

                {/* Menu Section */}
                <div className="space-y-1">
                  {getNavigationItems(isSelfHosted).map(renderNavigationItem)}
                </div>
              </>
            ) : (
              <div className="flex flex-col justify-center items-start gap-3">
                <a
                  className="flex h-9 justify-center items-center rounded-full bg-[#1B242D] dark:bg-[rgb(var(--primary))] text-sm text-white dark:text-[rgb(var(--primary-foreground))] hover:bg-[#2C3642] dark:hover:opacity-90 transition-colors py-2 w-full"
                  href={`/api/auth/login?returnTo=${encodeURIComponent(pathname)}`}>
                  Sign Up
                </a>
                <a
                  className="flex h-9 justify-center items-center rounded-full border border-[#E2E2E2] dark:border-[rgb(var(--border))] bg-white dark:bg-[rgb(var(--card))] text-sm text-black dark:text-white hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors py-2 w-full"
                  href={`/api/auth/login?returnTo=${encodeURIComponent(pathname)}`}>
                  Log in
                </a>
              </div>
            )}
          </div>

          {/* Footer Section */}
          <div className="w-full space-y-6 mt-auto pt-6 border-t border-[#E2E2E2] dark:border-[rgb(var(--border))]">
            {/* Social Links */}
            <div className="space-y-2">
              <Link
                className="flex h-8 px-2 justify-center items-center gap-2 rounded 
                  bg-[#5865F2] text-white text-sm w-full 
                  hover:bg-[#4752C4] active:bg-[#3C45B2] 
                  transition-all duration-200"
                href="https://discord.gg/9CMRSQPqx6"
                prefetch={false}
                target="_blank">
                <Icon className="w-5 h-5" icon="simple-icons:discord" />
                Join Discord
              </Link>
              <Link
                className="flex h-8 px-2 justify-center items-center gap-2 rounded 
                  border border-[#E2E2E2] dark:border-[rgb(var(--border))] bg-white dark:bg-[rgb(var(--card))] text-[#191919] dark:text-[rgb(var(--foreground))] text-sm w-full
                  hover:bg-[#F5F5F5] dark:hover:bg-gray-800 active:bg-[#EAEAEA] dark:active:bg-gray-700
                  transition-all duration-200"
                href="https://x.com/gurubaseio"
                prefetch={false}
                target="_blank">
                <Icon
                  className="w-5 h-5 text-[#191919] dark:text-[rgb(var(--foreground))]"
                  icon="ri:twitter-x-fill"
                />
                Follow Us
              </Link>
              <Link
                className="flex h-8 px-2 justify-center items-center gap-2 rounded 
                  border border-[#E2E2E2] dark:border-[rgb(var(--border))] bg-white dark:bg-[rgb(var(--card))] text-[#191919] dark:text-[rgb(var(--foreground))] text-sm w-full
                  hover:bg-[#F5F5F5] dark:hover:bg-gray-800 active:bg-[#EAEAEA] dark:active:bg-gray-700
                  transition-all duration-200"
                href="https://github.com/Gurubase/gurubase?utm_source=gurubase&utm_medium=mobile_menu&utm_campaign=social"
                prefetch={false}
                target="_blank">
                <Icon
                  className="w-5 h-5 text-[#191919] dark:text-[rgb(var(--foreground))]"
                  icon="simple-icons:github"
                />
                Star Us
              </Link>
            </div>

            {/* Legal Links */}
            <div className="flex items-center justify-center gap-2 text-xs text-[#6D6D6D] dark:text-gray-400">
              <Link
                className="hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
                href="/privacy-policy"
                prefetch={false}>
                Privacy Policy
              </Link>
              <span>•</span>
              <Link
                className="hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
                href="/terms-of-use"
                prefetch={false}>
                Terms of Use
              </Link>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default MobileSidebar;
