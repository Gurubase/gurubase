import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { getDataForSlugDetails } from "@/app/actions";
import { CalendarIcon } from "@/components/Icons";
import { useAppSelector } from "@/redux/hooks";

export default function AnswerLastModified({
  initialDateUpdated,
  bingeId = null
}) {
  const { slug, guruType } = useParams();
  const [dateUpdated, setDateUpdated] = useState(initialDateUpdated);
  const streamingStatus = useAppSelector(
    (state) => state.mainForm.streamingStatus
  );

  const postContentExist = useAppSelector(
    (state) => state.mainForm.postContentExist
  );

  const reduxDateUpdated = useAppSelector(
    (state) => state.mainForm.dateUpdated
  );

  useEffect(() => {
    const fetchLastModified = async () => {
      const response = await getDataForSlugDetails(slug, guruType, bingeId);
      const { msg } = JSON.parse(response);

      if (!response || msg?.toLowerCase() === "question not found") {
        setDateUpdated(null);

        return;
      }
      const { date_updated } = JSON.parse(response);

      setDateUpdated(date_updated);
    };

    if (reduxDateUpdated) {
      setDateUpdated(reduxDateUpdated);

      return;
    }

    if (dateUpdated) {
      setDateUpdated(dateUpdated);

      return;
    }

    if (
      streamingStatus === false &&
      slug &&
      guruType &&
      !initialDateUpdated &&
      postContentExist
    ) {
      fetchLastModified();
    }
  }, [
    initialDateUpdated,
    streamingStatus,
    slug,
    guruType,
    postContentExist,
    reduxDateUpdated,
    dateUpdated,
    bingeId
  ]);

  if (!dateUpdated) return null;

  return (
    <div className="flex items-center gap-1 pb-4 mx-6">
      <CalendarIcon />
      <span className="text-[14px] font-inter font-normal text-[#6D6D6D]">
        Last Modified:
      </span>
      <span className="text-[14px] font-inter font-medium text-[#191919]">
        {dateUpdated}
      </span>
    </div>
  );
}
