import React, { useEffect, useState } from "react";

import { useAppSelector } from "@/redux/hooks";

import SourceItem from "./SourceItem";

const ArticleSources = ({ references }) => {
  const [sources, setSources] = useState(references || []);

  const reduxReferences = useAppSelector((state) => state.mainForm.references);

  useEffect(() => {
    if (reduxReferences?.length) {
      setSources(reduxReferences);

      return;
    }

    if (references?.length) {
      setSources(references);
    }
  }, [references, reduxReferences]);

  if (
    !sources?.length ||
    sources.every((source) => !source.question)
  ) {
    return null;
  }

  return (
    <>
      <header className="text-base font-semibold text-gray-800 max-md:max-w-full">
        Sources
      </header>
      <div className="flex flex-col mt-3 w-full text-sm font-medium text-zinc-900 max-md:max-w-full">
        {sources?.map((source, index) => (
          <SourceItem
            key={"source" + index}
            iconUrl={source?.icon}
            link={source?.link}
            question={source?.question}
          />
        ))}
      </div>
    </>
  );
};

export default ArticleSources;
