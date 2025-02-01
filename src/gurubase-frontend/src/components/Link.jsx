"use client";
import NextLink from "next/link";
import { useAppNavigation } from "@/lib/navigation";

export const Link = ({ children, ...props }) => {
  const navigation = useAppNavigation();

  const handleClick = (e) => {
    // If it's an external link or has a target, don't handle it
    if (props.target || props.href.startsWith("http")) {
      return;
    }

    // If there's an onClick handler already, call it
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
