import { useUser } from "@auth0/nextjs-auth0/client";
import { Icon } from "@iconify/react";
import clsx from "clsx";
import { usePathname } from "next/navigation";
import { memo, useState } from "react";

import GuruBaseLogo from "@/components/GuruBaseLogo";
import {
  getGuruPromptMap,
  getGuruTypeTextColor
} from "@/components/Header/utils";
import { Link } from "@/components/Link";
import MobileOtherGurus from "@/components/OtherGurus/MobileOtherGurus";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from "@/components/ui/dropdown-menu";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { useAppNavigation } from "@/lib/navigation";
import { useAppDispatch, useAppSelector } from "@/redux/hooks";
import { setResetMainForm } from "@/redux/slices/mainFormSlice";

import MobileSidebar from "./MobileSidebar";
import { getNavigationItems } from "./navigationConfig";
import SocialMediaHeader from "./SocialMediaHeader";

// Create a memoized UserAvatar component with loading optimization
const UserAvatar = memo(({ user }) => {
  if (!user.picture) {
    return (
      <Avatar className="h-8 w-8 border border-gray-200 bg-gray-100">
        <AvatarFallback className="bg-gray-100 text-gray-600">
          {(user.name ? user.name.charAt(0).toUpperCase() : null) || "U"}
        </AvatarFallback>
      </Avatar>
    );
  }

  return (
    <div className="relative h-8 w-8">
      <Avatar className="h-8 w-8 border border-gray-200">
        <AvatarImage
          alt={user.name}
          className="object-cover"
          loading="eager"
          src={user.picture}
        />
        <AvatarFallback>
          {(user.name ? user.name.charAt(0).toUpperCase() : null) || "U"}
        </AvatarFallback>
      </Avatar>
      <div className="absolute inset-0 rounded-full shadow-inner" />
    </div>
  );
});

UserAvatar.displayName = "UserAvatar";

// Add this new component for self-hosted avatar with memo
const SelfHostedAvatar = memo(() => (
  <Avatar className="h-8 w-8">
    <AvatarFallback>
      <Icon className="h-5 w-5 text-gray-400" icon="solar:user-linear" />
    </AvatarFallback>
  </Avatar>
));

SelfHostedAvatar.displayName = "SelfHostedAvatar";

const Header = memo(({ guruType, allGuruTypes, sidebarExists = false }) => {
  const pathname = usePathname();
  const dispatch = useAppDispatch();
  const isLoading = useAppSelector((state) => state.mainForm.isLoading);
  const postContentExist = useAppSelector(
    (state) => state.mainForm.postContentExist
  );
  const navigation = useAppNavigation();

  const isSelfHosted = process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted";
  const { user, isLoading: isUserLoading } = isSelfHosted
    ? { user: true, isLoading: false }
    : useUser();
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const isMobile = useMediaQuery("(max-width: 915px)");

  const renderNavigationItem = (item) => (
    <DropdownMenuItem key={item.id} className="p-0.5">
      <div className="w-full">
        <Link
          className="flex items-center gap-2 p-2 rounded-lg hover:bg-[#F5F5F5] transition-colors cursor-pointer w-full"
          href={item.href}
          prefetch={false}>
          <Icon
            className={`w-4 h-4 text-[${item.iconColor}]`}
            icon={item.icon}
          />
          <span
            className={`flex-1 text-sm font-medium text-[${item.textColor}] overflow-hidden text-ellipsis whitespace-nowrap leading-[1.25]`}>
            {item.label}
          </span>
        </Link>
      </div>
    </DropdownMenuItem>
  );

  const renderAuthButtons = () => {
    // Show loading spinner while user data is being fetched
    if (!isSelfHosted && isUserLoading) {
      return (
        <div className="guru-sm:hidden">
          <div className="flex items-center gap-2 p-1 rounded-full">
            <div className="flex items-center justify-center h-8 w-8 rounded-full border border-gray-200 bg-gray-100 animate-pulse" />
          </div>
        </div>
      );
    }

    if (user) {
      return (
        <div className="guru-sm:hidden">
          <DropdownMenu>
            <DropdownMenuTrigger className="focus:outline-none">
              <div className="flex items-center gap-2 p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                {isSelfHosted ? (
                  <SelfHostedAvatar />
                ) : (
                  <UserAvatar user={user} />
                )}
                <span className="sr-only">User menu</span>
              </div>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="end"
              className="w-[220px] p-0.5 rounded-[10px] border-[0.5px] border-[#E2E2E2] bg-white shadow-[4px_4px_10px_0px_rgba(210,210,210,0.20)]">
              {!isSelfHosted && (
                <>
                  <DropdownMenuLabel className="px-3 py-2.5">
                    <div className="flex flex-col space-y-1.5">
                      <p className="text-sm font-medium leading-[1.25]">
                        {user.name}
                      </p>
                      <p className="text-xs leading-[1.25] text-muted-foreground">
                        {user.email}
                      </p>
                    </div>
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator className="bg-[#E2E2E2]" />
                </>
              )}
              {getNavigationItems(isSelfHosted).map(renderNavigationItem)}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      );
    }

    return (
      <div className="flex items-center gap-3 guru-sm:hidden">
        <a
          className="flex h-9 px-4 justify-center items-center gap-2 rounded-full border border-[#E2E2E2] bg-white text-sm font-medium text-black hover:bg-gray-50 transition-colors"
          href={`/api/auth/login?returnTo=${encodeURIComponent(pathname)}`}>
          Log in
        </a>
        <a
          className="flex h-9 px-4 items-center gap-1.5 rounded-full bg-[#1B242D] text-sm font-medium text-white hover:bg-[#2C3642] transition-colors"
          href={`/api/auth/login?returnTo=${encodeURIComponent(pathname)}`}>
          Sign Up
        </a>
      </div>
    );
  };

  const getBackgroundColor = () => {
    return "#FFFFFF";
  };

  const activeGuruName = useAppSelector(
    (state) => state.mainForm.activeGuruName
  );

  const isLongGuruName = activeGuruName && activeGuruName.length >= 14;

  const handleRedirectToHome = () => {
    dispatch(setResetMainForm());
    navigation.setHref("/");
  };

  return (
    <div className="relative">
      <div
        className={clsx(
          isMobileSidebarOpen && "guru-sm:hidden",
          guruType ? "h-[81px] guru-sm:h-[64px] guru-md:h-[81px]" : "h-[64px]"
        )}
      />
      <header
        className={clsx(
          "flex justify-center items-start px-6 guru-sm:px-0 w-full guru-sm:w-full border-x border-[#E2E2E2] guru-sm:border-none border-b border-solid border-neutral-200 fixed top-0 bg-white",
          isMobile ? "z-51" : "z-50",
          isMobileSidebarOpen && "guru-sm:hidden",
          guruType || !guruType || postContentExist || isLoading
            ? "guru-sm:mt-0"
            : "guru-sm:mt-[10rem] ",
          guruType || !guruType || postContentExist || isLoading
            ? "guru-sm:mb-0"
            : "guru-sm:mb-8"
        )}
        style={{ backgroundColor: getBackgroundColor() }}>
        <div
          className={clsx(
            "flex guru-sm:flex-wrap gap-5 justify-between guru-sm:px-5 flex-grow shrink",
            "guru-sm:justify-between guru-sm:items-center",
            "py-3",
            sidebarExists
              ? "max-w-[1440px]"
              : "guru-md:max-w-[870px] guru-lg:max-w-[1180px]"
          )}>
          {/* Mobile Header Row */}
          <div className="hidden guru-sm:flex items-center justify-between w-full gap-6">
            <div className="flex items-center gap-4">
              <button
                aria-label="Open menu"
                className="flex items-center justify-center w-8 h-8 text-gray-700"
                onClick={() => setIsMobileSidebarOpen(true)}>
                <Icon className="w-6 h-6" icon="solar:hamburger-menu-outline" />
              </button>
              <Link
                className="cursor-pointer"
                href="/"
                prefetch={false}
                onClick={handleRedirectToHome}>
                <div className={clsx(isLongGuruName && "scale-75 -ml-4")}>
                  <GuruBaseLogo
                    allGuruTypes={allGuruTypes}
                    guruType={guruType}
                  />
                </div>
              </Link>
            </div>
            <MobileOtherGurus
              allGuruTypes={allGuruTypes}
              isLongGuruName={isLongGuruName}
            />
          </div>

          {/* Desktop Logo */}
          <div
            className={clsx(
              "flex gap-2 my-auto text-xs font-bold guru-sm:hidden"
            )}
            style={{ color: getGuruTypeTextColor(guruType, allGuruTypes) }}>
            <div className="flex flex-col">
              <Link
                className="cursor-pointer"
                href="/"
                prefetch={false}
                onClick={handleRedirectToHome}>
                <div className="mt-0 ml-1">
                  {guruType && activeGuruName
                    ? activeGuruName
                    : guruType
                      ? getGuruPromptMap(guruType, allGuruTypes)
                      : ""}
                </div>
                <GuruBaseLogo allGuruTypes={allGuruTypes} guruType={guruType} />
              </Link>
            </div>
          </div>

          <div className="flex items-center gap-4 guru-sm:hidden">
            <SocialMediaHeader />
            {renderAuthButtons()}
          </div>

          {isMobile && (
            <MobileSidebar
              isOpen={isMobileSidebarOpen}
              user={user}
              onClose={() => setIsMobileSidebarOpen(false)}
            />
          )}
        </div>
      </header>
    </div>
  );
});

Header.displayName = "Header";

export default Header;
