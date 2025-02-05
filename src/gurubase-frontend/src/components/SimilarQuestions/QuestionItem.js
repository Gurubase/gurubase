import Image from "next/image";
import { useParams } from "next/navigation";
import React from "react";

import stars from "@/assets/images/stars.svg";
import { Link } from "@/components/Link";

function QuestionItem({ text, slug, isLast, isMobile }) {
  const { guruType } = useParams(); // Use useParams to get the dynamic route parameters

  return (
    <Link
      className="guru-md:h-full w-full"
      href={`/g/${guruType}/${slug}`}
      prefetch={false}>
      <div
        className={`cursor-pointer flex gap-3 items-center px-3 py-4 w-full guru-md:h-full guru-md:border-[1px] guru-md:border-gray-85 guru-md:flex-col guru-md:min-w-[140px] guru-md:gap-4 guru-md:rounded-xl guru-md:mx-1 guru-md:border-opacity-50 hover:bg-black-50 ${
          isLast ? "border-none" : "border-b-[0.5px] border-b-gray-85"
        }`}>
        <Image
          alt={"icon with stars"}
          className="object-contain shrink-0 self-stretch my-auto w-5 aspect-square"
          height={24}
          loading="lazy"
          src={stars}
          width={119}
        />
        <div className="flex-1 shrink self-stretch my-auto break-words">
          {text}
        </div>
      </div>
    </Link>
  );
}

export default QuestionItem;
