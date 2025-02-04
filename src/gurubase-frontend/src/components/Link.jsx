"use client";
import NextLink from "next/link";
import { useAppNavigation } from "@/lib/navigation";

export const Link = ({ children, ...props }) => {
  const navigation = useAppNavigation();

  const handleClick = (e) => {
    // Only handle internal non-auth links with custom navigation
    if (
      !props.href.startsWith("/api/auth/") &&
      !props.href.startsWith("http") &&
      !props.target
    ) {
      e.preventDefault();
      navigation.push(props.href);
    }

    if (props.onClick) {
      props.onClick(e);
    }
  };

  return (
    <NextLink {...props} onClick={handleClick}>
      {children}
    </NextLink>
  );
};
