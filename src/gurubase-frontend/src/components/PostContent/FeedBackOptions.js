"use client";
import { recordVote } from "@/utils/clientActions";
import { getFingerPrint } from "@/utils/common";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import {
  CarbonClose,
  MdiLightThumbDown,
  MdiLightThumbUp
} from "@/components/Icons";

const FeedBackOptions = ({ isHelpful }) => {
  const [feedbackState, setFeedbackState] = useState(false);
  const [fingerPrint, setFingerPrint] = useState(null);
  const { guruType, slug } = useParams(); // Use useParams to get the dynamic route parameters

  const handleFeedback = async (feedback) => {
    if (feedback === "close") {
      setFeedbackState(true);
    } else {
      setFeedbackState(feedback);
      handeVote(feedback === "1" ? "upvote" : "downvote");
    }
  };

  const handeVote = (vote) => {
    recordVote(slug, fingerPrint, vote, guruType).then((result) =>
      setFeedbackState(true)
    );
    // .catch((error) => console.error("Error recording vote:", error));
  };

  useEffect(() => {
    if (fingerPrint || typeof window === "undefined") return;
    getFingerPrint().then((fp) => setFingerPrint(fp));
  }, []);

  return (
    <div
      className={`flex gap-4 justify-center pl-4 bg-white rounded-md border border-solid border-neutral-200 h-9 ${
        feedbackState && "hidden"
      }`}>
      <p className="my-auto text-sm font-medium text-center text-zinc-900 xs:hidden">
        Is this article helpful?
      </p>
      <p className="my-auto text-sm font-medium text-center text-zinc-900 xs:block hidden">
        Helpful?
      </p>
      <div className="flex flex-row">
        <div className="flex gap-4">
          <button
            onClick={() => handleFeedback("1")}
            aria-label="icon with thumb up">
            <MdiLightThumbUp className="text-gray-400" width={20} height={20} />
          </button>
          <button
            onClick={() => handleFeedback("0")}
            className=" text-gray-400"
            aria-label="icon with thumb down">
            <MdiLightThumbDown
              className="text-gray-400"
              width={20}
              height={20}
            />
          </button>
        </div>
        <div className="flex gap-4">
          <div className="shrink-0 w-4 bg-white" />
        </div>
        <div className="flex justify-center items-center px-3 py-2.5 border-l border-solid border-neutral-200">
          <button
            onClick={() => handleFeedback("close")}
            aria-label="icon with close">
            <CarbonClose className="text-gray-400" width={16} height={16} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default FeedBackOptions;
