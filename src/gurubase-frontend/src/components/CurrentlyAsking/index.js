"use client";

import { motion } from "framer-motion";
import { Check, X } from "lucide-react";
import { cn } from "@/lib/utils";
import Image from "next/image";
import loadingSpinner from "@/assets/animations/loading_spinner.gif";

const LoadingSpinner = () => (
  <div className="flex h-6 w-6 items-center justify-center">
    <Image
      src={loadingSpinner}
      alt="Loading..."
      width={24}
      height={24}
      className="object-contain"
    />
  </div>
);

export default function CurrentlyAsking({
  isLoading,
  slugPageRendered,
  streamingStatus,
  guruTypeName,
  askingQuestion,
  waitingForFirstChunk,
  answerErrorType
}) {
  if (!askingQuestion) {
    return null;
  }

  const steps = [
    {
      id: "1",
      text: `Finding the best contexts from ${guruTypeName} sources.`,
      isComplete:
        (isLoading && !slugPageRendered && !streamingStatus) || // /summary/ request
        (streamingStatus && !slugPageRendered), // /answer/ request
      isFailed: answerErrorType === "answerIsInvalid"
    },
    {
      id: "2",
      text: "Evaluating sources to prevent hallucinations.",
      isComplete: !waitingForFirstChunk && !slugPageRendered && streamingStatus,
      isFailed: answerErrorType === "context" || answerErrorType === "stream"
    }
  ];

  if (!isLoading && (slugPageRendered || !streamingStatus)) {
    return null;
  }

  // Find the index of the first incomplete step
  const firstIncompleteIndex = steps.findIndex((step) => !step.isComplete);

  return (
    <div className="flex justify-center w-full pt-10">
      <div className={cn("space-y-4")}>
        {steps.map((step, index) => {
          // Only show if step is complete, failed, OR if it's the first incomplete step
          if (
            !step.isComplete &&
            !step.isFailed &&
            index !== firstIncompleteIndex
          ) {
            return null;
          }

          return (
            <div key={step.id} className="flex items-center gap-3 h-6 pb-10">
              {step.isFailed ? (
                <div className="flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-white">
                  <X className="h-3 w-3" />
                </div>
              ) : step.isComplete ? (
                <div className="flex h-5 w-5 items-center justify-center rounded-full bg-green-500 text-white">
                  <Check className="h-3 w-3" />
                </div>
              ) : (
                <div className="flex h-6 items-center">
                  <LoadingSpinner />
                </div>
              )}
              <span
                className="text-[14px] font-inter font-medium text-[#191919]"
                style={{ lineHeight: "normal" }}>
                {step.text}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
