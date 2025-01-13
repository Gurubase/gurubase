"use client";
import { Icon } from "@iconify/react";
import React, { useEffect, useMemo, useState } from "react";

import {
  DeviconLinkedin,
  LineMdTwitterXAlt,
  LogosRedditIcon,
  SolarCopyBold,
  SolarShareOutline
} from "@/components/Icons";

const ShareOptions = ({ title, description }) => {
  const [isCopied, setIsCopied] = useState(false);
  const [postUrl, setPostUrl] = useState();

  const handleShare = (platform) => {
    if (typeof window !== "undefined") {
      window.open(platform, "_blank");
    }
  };

  const handleCopyLink = () => {
    if (typeof navigator !== "undefined") {
      navigator?.clipboard.writeText(postUrl);
      setIsCopied(true);
    }
  };

  useEffect(() => {
    if (isCopied) {
      const timer = setTimeout(() => {
        setIsCopied(false);
      }, 2000);

      return () => clearTimeout(timer);
    }
  }, [isCopied]);

  // get page url with slug
  useEffect(() => {
    if (typeof window !== "undefined") {
      const url = window.location.href;

      setPostUrl(url.split("?question")[0]);
    }
  }, []);

  const handleMobileShare = () => {
    if (typeof navigator !== "undefined" && navigator?.share) {
      navigator.share({
        title: typeof document !== "undefined" ? document.title : title,
        text: description,
        url: typeof window !== "undefined" ? window.location.href : postUrl
      });
      // .catch((error) => console.error("Error sharing:", error));
    } else {
      alert("Web Share API is not supported in your browser.");
    }
  };

  const options = useMemo(
    () => [
      {
        icon: <SolarCopyBold height={16} width={16} />,
        alt: "Copy Link",
        text: "Copy Link"
      },
      {
        icon: <LineMdTwitterXAlt height={16} width={16} />,
        alt: "Share to X",
        text: "Share on X",
        shareLink: `https://twitter.com/intent/tweet?url=${postUrl}/&text=${title}`
      },
      {
        icon: <LogosRedditIcon height={16} width={16} />,
        alt: "Share to Reddit",
        text: "Share on Reddit",
        shareLink: `https://www.reddit.com/submit?url=${postUrl}/&title=${title}`
      },
      {
        icon: <DeviconLinkedin height={16} width={16} />,
        alt: "Share to Linkedin",
        text: "Share on Linkedin",
        shareLink: `https://www.linkedin.com/shareArticle?mini=true&url=${postUrl}/&title=${title}&summary=${title}&source=LinkedIn`
      }
    ],
    [postUrl, title]
  );

  return (
    <>
      {/* Desktop Share Options */}
      <div className="guru-sm:hidden flex gap-3 flex-wrap px-5 xs:px-0 sm:px-0 text-sm font-medium text-center text-black-600 xs:flex-wrap">
        {options.map((option, index) => (
          <button
            key={index}
            aria-label={option.alt}
            className="flex gap-2 justify-center items-center px-4 h-9  bg-white rounded-md border border-solid border-neutral-200"
            onClick={() => {
              if (index === 0) {
                handleCopyLink();
              } else {
                handleShare(option.shareLink);
              }
            }}>
            {option.icon ? (
              isCopied && index === 0 ? (
                <Icon height="24" icon="heroicons:check-16-solid" width="26" />
              ) : React.isValidElement(option.icon) ? (
                option.icon
              ) : (
                <span dangerouslySetInnerHTML={{ __html: option.icon }} />
              )
            ) : null}
            <p className="truncate min-w-20">
              {isCopied && index === 0 ? "Link Copied" : option.text}
            </p>
          </button>
        ))}
      </div>
      {/* Mobile Share Option */}
      <div className="guru-sm:flex hidden  gap-3 flex-wrap  xs:px-0 sm:px-0 h-9 text-sm font-medium text-center text-zinc-900 xs:flex-wrap">
        <button
          key={"mobile-share-button"}
          aria-label="icon with share"
          className="flex gap-2 justify-center items-center px-4 h-19 text-black-600 bg-white rounded-md border border-solid border-gray-85 "
          onClick={handleMobileShare}>
          <SolarShareOutline className="text-gray-400" height={16} width={16} />

          <p className="truncate">Share</p>
        </button>
      </div>
    </>
  );
};

export default ShareOptions;
