"use client";
import React, { useEffect, useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { atomDark } from "react-syntax-highlighter/dist/esm/styles/prism";

import { SolarCheckReadLinear, SolarCopyBold } from "@/components/Icons";
import { useAppSelector } from "@/redux/hooks";

const CodeBlock = ({ language, value }) => {
  const [isCopied, setIsCopied] = useState(false);
  const [isCopySupported, setIsCopySupported] = useState(true);

  const isStreaming = useAppSelector((state) => state.mainForm.streamingStatus);

  // check if the browser supports the clipboard API and copy the code block to the clipboard
  useEffect(() => {
    if (typeof navigator !== "undefined" && !navigator?.clipboard) {
      setIsCopySupported(false);
    }
  }, []);

  const copyToClipboard = (text) => {
    if (typeof navigator !== "undefined" && navigator?.clipboard) {
      navigator?.clipboard.writeText(text).then(
        () => {
          // after 5 seconds set isCopied to false
          setIsCopied(true);
          setTimeout(() => {
            setIsCopied(false);
          }, 2500);
        },
        () => {
          setIsCopied(false);
        }
      );
    } else {
      setIsCopySupported(false);
    }
  };

  return (
    <div className="relative not-prose">
      {isCopySupported && !isStreaming && (
        <button
          aria-label="icon with copy"
          className="absolute top-2 right-2 bg-transparent p-1 text-sm rounded focus:outline-none focus:ring-1 focus:ring-gray-500 focus:ring-opacity-0"
          onClick={() => copyToClipboard(value)}>
          {/* if isCopied is true set Icon with tick else set content-copy icon  */}
          {isCopied ? (
            <SolarCheckReadLinear
              className=" text-white hover:text-gray-85"
              height={20}
              width={20}
            />
          ) : (
            <SolarCopyBold
              className=" text-white hover:text-gray-85"
              height={16}
              width={16}
            />
          )}
        </button>
      )}
      <SyntaxHighlighter
        language={language === "razor" ? "csharp" : language}
        style={atomDark}>
        {value}
      </SyntaxHighlighter>
    </div>
  );
};

export default CodeBlock;
