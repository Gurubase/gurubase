import Image from "next/image";
import { usePathname } from "next/navigation";
import React from "react";

import { SettingsIcon } from "@/components/Icons";
import { Link } from "@/components/Link";
import { useAppNavigation } from "@/lib/navigation";
import { useAppDispatch } from "@/redux/hooks";
import { resetErrors, setResetMainForm } from "@/redux/slices/mainFormSlice";

const GuruItem = ({ slug, icon, text }) => {
  const dispatch = useAppDispatch();
  const pathname = usePathname();
  const isMyGurusPage = pathname === "/my-gurus";
  const isSelfHosted = process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted";
  const navigation = useAppNavigation();

  const handleClick = (e) => {
    e.preventDefault();
    dispatch(setResetMainForm());
    dispatch(resetErrors());

    // If we're on the My Gurus page, use the custom guru URL pattern
    if (isMyGurusPage) {
      navigation.setHref(`/guru/${slug}`);
    } else {
      navigation.setHref(`/g/${slug}`);
    }
  };

  const handleSettingsClick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    navigation.setHref(`/guru/${slug}`);
  };

  return (
    <Link
      href={isMyGurusPage ? `/guru/${slug}` : `/g/${slug}`}
      prefetch={false}
      onClick={handleClick}>
      <div className="flex gap-3 items-center px-3 py-2 w-full whitespace-nowrap border-solid border-b-[0.5px] border-b-neutral-200 hover:bg-black-50 cursor-pointer">
        {icon &&
          (isSelfHosted ? (
            <Image
              alt={text + " guru icon"}
              className="object-contain shrink-0 self-stretch my-auto w-9 aspect-square p-[6px] rounded-full bg-gray-25"
              height={24}
              src={icon}
              width={24}
            />
          ) : (
            <img
              alt={text + " guru icon"}
              className="object-contain shrink-0 self-stretch my-auto w-9 aspect-square p-[6px] rounded-full bg-gray-25"
              height={24}
              loading="lazy"
              src={icon}
              width={24}
            />
          ))}
        <div className="flex-1 shrink self-stretch my-auto basis-0">{text}</div>
        {isSelfHosted && (
          <div
            aria-label="Settings"
            className="p-2 hover:bg-gray-50 rounded-full transition-colors"
            role="button"
            tabIndex={0}
            onClick={handleSettingsClick}>
            <SettingsIcon className="text-gray-500 hover:text-gray-700" />
          </div>
        )}
      </div>
    </Link>
  );
};

export default GuruItem;
