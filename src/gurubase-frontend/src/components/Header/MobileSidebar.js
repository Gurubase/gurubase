import { Icon } from "@iconify/react";
import { usePathname } from "next/navigation";
import { useEffect } from "react";

import GuruBaseLogo from "@/components/GuruBaseLogo";
import { Link } from "@/components/Link";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { useAppNavigation } from "@/lib/navigation";

const MobileSidebar = ({ isOpen, onClose, user }) => {
  const pathname = usePathname();
  const navigation = useAppNavigation();

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

  const handleNavigate = (path) => {
    const returnTo = encodeURIComponent(pathname);

    navigation.push(`${path}?returnTo=${returnTo}`);
  };

  const isSelfHosted = process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted";

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent
        className="fixed left-0 top-0 h-full w-[240px] p-0 border-r border-[#E2E2E2] bg-white shadow-lg 
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
                <div className="pb-6 border-b border-[#E2E2E2]">
                  <div className="flex flex-col">
                    <p className="text-base font-semibold text-[#191919] mb-1">
                      {user.name}
                    </p>
                    <p className="text-sm text-[#6D6D6D]">{user.email}</p>
                  </div>
                </div>

                {/* Menu Section */}
                <div className="space-y-1">
                  <Link
                    className="flex items-center gap-2 py-3 rounded-lg transition-all duration-200
                      hover:bg-[#F5F5F5] hover:pl-1 active:bg-[#EAEAEA]"
                    href="/my-gurus"
                    prefetch={false}
                    onClick={onClose}>
                    <Icon
                      className="w-5 h-5 text-[#6D6D6D]"
                      icon="solar:notes-linear"
                    />
                    <span className="text-sm text-[#6D6D6D]">My Gurus</span>
                  </Link>
                  <Link
                    className="flex items-center gap-2 py-3 rounded-lg transition-all duration-200
                      hover:bg-[#F5F5F5] hover:pl-1 active:bg-[#EAEAEA]"
                    href="/binge-history"
                    prefetch={false}
                    onClick={onClose}>
                    <Icon
                      className="w-5 h-5 text-[#6D6D6D]"
                      icon="solar:history-linear"
                    />
                    <span className="text-sm text-[#6D6D6D]">
                      Binge History
                    </span>
                  </Link>
                  {!isSelfHosted && (
                    <Link
                      className="flex items-center gap-2 py-3 rounded-lg transition-all duration-200
                        hover:bg-[#F5F5F5] hover:pl-1 active:bg-[#EAEAEA]"
                      href="/api/auth/logout">
                      <Icon
                        className="w-5 h-5 text-[#DC2626]"
                        icon="solar:logout-outline"
                      />
                      <span className="text-sm text-[#DC2626]">Log out</span>
                    </Link>
                  )}
                </div>
              </>
            ) : (
              <div className="flex flex-col justify-center items-start gap-3">
                <button
                  className="flex h-9 justify-center items-center rounded-full bg-[#1B242D] text-sm text-white hover:bg-[#2C3642] transition-colors py-2 w-full"
                  onClick={() => handleNavigate("/api/auth/login")}>
                  Sign Up
                </button>
                <button
                  className="flex h-9 justify-center items-center rounded-full border border-[#E2E2E2] bg-white text-sm text-black hover:bg-gray-50 transition-colors py-2 w-full"
                  onClick={() => handleNavigate("/api/auth/login")}>
                  Log in
                </button>
              </div>
            )}
          </div>

          {/* Footer Section */}
          <div className="w-full space-y-6 mt-auto pt-6 border-t border-[#E2E2E2]">
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
                  border border-[#E2E2E2] bg-white text-[#191919] text-sm w-full
                  hover:bg-[#F5F5F5] active:bg-[#EAEAEA]
                  transition-all duration-200"
                href="https://x.com/gurubaseio"
                prefetch={false}
                target="_blank">
                <Icon
                  className="w-5 h-5 text-[#191919]"
                  icon="ri:twitter-x-fill"
                />
                Follow Us
              </Link>
              <Link
                className="flex h-8 px-2 justify-center items-center gap-2 rounded 
                  border border-[#E2E2E2] bg-white text-[#191919] text-sm w-full
                  hover:bg-[#F5F5F5] active:bg-[#EAEAEA]
                  transition-all duration-200"
                href="https://github.com/Gurubase/gurubase?utm_source=gurubase&utm_medium=mobile_menu&utm_campaign=social"
                prefetch={false}
                target="_blank">
                <Icon
                  className="w-5 h-5 text-[#191919]"
                  icon="simple-icons:github"
                />
                Star Us
              </Link>
            </div>

            {/* Legal Links */}
            <div className="flex items-center justify-center gap-2 text-xs text-[#6D6D6D]">
              <Link
                className="hover:text-gray-800 transition-colors"
                href="/privacy-policy"
                prefetch={false}>
                Privacy Policy
              </Link>
              <span>•</span>
              <Link
                className="hover:text-gray-800 transition-colors"
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
