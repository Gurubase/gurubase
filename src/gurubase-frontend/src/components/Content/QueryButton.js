import Link from "next/link";
import React from "react";

import { toCapitalize } from "@/utils/common";

const QueryButton = ({ text, guruType, slug, onClick }) => {
  return (
    <Link
      className="flex justify-center xs:justify-start  xs:px-2 px-4 py-2.5 h-fit bg-white rounded-md border border-solid text-wrap border-neutral-200"
      href={`/g/${guruType}/${slug}`}
      prefetch={false}
      onClick={onClick}>
      {
        // capitalize the first letter of the text
        toCapitalize(text)
      }
    </Link>
  );
};

export default QueryButton;
