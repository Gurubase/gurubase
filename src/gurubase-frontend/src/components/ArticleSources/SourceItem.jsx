import { Lock } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import React from "react";

import AINetworkSpark from "@/assets/images/ai-network-spark.svg";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from "@/components/ui/tooltip";

function SourceItem({ link, question, iconUrl }) {
  if (!question.length || !iconUrl.length) return null;

  const shouldShowTooltip = question.length > 90;
  const displayedQuestion = shouldShowTooltip
    ? question.slice(0, 90) + "..."
    : question;

  const Content = () => (
    <article
      className={`flex flex-wrap gap-3 items-center p-4 mt-2 w-full bg-white rounded-xl border border-solid border-neutral-200 max-md:max-w-full ${link ? "hover:underline" : ""}`}>
      <div className="flex items-center gap-3">
        <Image
          alt="ai-sources"
          className="object-contain shrink-0 self-stretch my-auto w-5 aspect-square"
          height={20}
          loading="lazy"
          src={iconUrl || AINetworkSpark}
          width={20}
        />
      </div>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <p
              className={`flex-1 shrink self-stretch my-auto w-full overflow-hidden whitespace-nowrap text-ellipsis`}>
              {displayedQuestion}
            </p>
          </TooltipTrigger>
          {shouldShowTooltip && (
            <TooltipContent className="max-w-xs" side="bottom">
              <p className="text-body3">{question}</p>
            </TooltipContent>
          )}
        </Tooltip>
      </TooltipProvider>
    </article>
  );

  return link ? (
    <Link href={link} prefetch={false} target="_blank">
      <Content />
    </Link>
  ) : (
    <Content />
  );
}

export default SourceItem;
