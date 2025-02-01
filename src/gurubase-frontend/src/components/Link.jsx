"use client";
import NextLink from "next/link";
import { useAppNavigation } from "@/lib/navigation";

export const Link = ({ children, ...props }) => {
  const navigation = useAppNavigation();

  const handleClick = (e) => {
    // Don't handle auth-related links, external links, or links with targets
    if (
      props.target ||
      props.href.startsWith("http") ||
      props.href.startsWith("/api/auth/")
    ) {
      if (props.onClick) {
        props.onClick(e);
      }
      return;
    }

    e.preventDefault(); // Prevent default navigation

    // Handle internal navigation
    navigation.push(props.href);
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
