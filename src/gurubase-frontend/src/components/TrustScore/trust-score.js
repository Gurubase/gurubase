import { InfoIcon } from "lucide-react";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { useAppSelector } from "@/redux/hooks";

import { cn } from "../../lib/utils";
import { Card } from "../ui/card";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from "../ui/tooltip";

export default function TrustScore({ score, className, bingeId = null }) {
  const { slug, guruType } = useParams();
  const [trustScore, setTrustScore] = useState(score || null);

  const streamingStatus = useAppSelector(
    (state) => state.mainForm.streamingStatus
  );

  const reduxTrustScore = useAppSelector((state) => state.mainForm.trustScore);

  const [isTooltipOpen, setIsTooltipOpen] = useState(false);
  const [isTouchDevice, setIsTouchDevice] = useState(false);

  useEffect(() => {
    setIsTouchDevice("ontouchstart" in window);
  }, []);

  useEffect(() => {
    const getTrustScore = async () => {
      if (score) {
        const { trust_score } = score;

        setTrustScore(trust_score);
      }
    };

    if (reduxTrustScore) {
      setTrustScore(reduxTrustScore);

      return;
    }

    if (score) {
      setTrustScore(score);
    }

    if (streamingStatus === false && slug && guruType && !score) {
      getTrustScore();
    }
  }, [score, reduxTrustScore, streamingStatus, slug, guruType, bingeId]);

  useEffect(() => {
    // Handle clicks outside for mobile
    if (isTouchDevice && isTooltipOpen) {
      const handleClickOutside = (e) => {
        const target = e.target;

        if (!target.closest('[role="tooltip"]') && !target.closest("button")) {
          setIsTooltipOpen(false);
        }
      };

      document.addEventListener("click", handleClickOutside);

      return () => document.removeEventListener("click", handleClickOutside);
    }
  }, [isTooltipOpen, isTouchDevice]);

  const handleTooltipChange = useCallback(
    (open) => {
      if (!isTouchDevice) {
        // For desktop: follow hover state
        setIsTooltipOpen(open);
      }
    },
    [isTouchDevice]
  );

  const handleButtonClick = useCallback(
    (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (isTouchDevice) {
        // For mobile: toggle on tap
        setIsTooltipOpen(!isTooltipOpen);
      }
    },
    [isTouchDevice, isTooltipOpen]
  );

  const filledCells = Math.floor(trustScore / 10);

  const getColors = (score) => {
    if (score >= 90) return { bg: "bg-emerald-500", text: "text-emerald-500" };
    if (score >= 80) return { bg: "bg-green-500", text: "text-green-500" };
    if (score >= 70) return { bg: "bg-lime-500", text: "text-lime-500" };
    if (score >= 60) return { bg: "bg-yellow-500", text: "text-yellow-500" };
    if (score >= 50) return { bg: "bg-orange-400", text: "text-orange-400" };
    if (score >= 40) return { bg: "bg-orange-500", text: "text-orange-500" };
    if (score >= 30) return { bg: "bg-red-400", text: "text-red-400" };
    if (score >= 20) return { bg: "bg-red-500", text: "text-red-500" };

    return { bg: "bg-red-600", text: "text-red-600" };
  };

  const { bg, text } = getColors(trustScore);

  if (trustScore === null || trustScore === 0 || trustScore === undefined) {
    return null;
  }

  return (
    <Card className={cn("pt-4 w-full font-inter", className)}>
      <div className="flex flex-row sm:flex-col sm:items-start gap-2">
        <div className="flex items-center gap-1">
          <h2 className="text-[#6D6D6D] font-inter text-right text-sm font-medium">
            Trust Score
          </h2>
          <span className={cn("text-sm font-semibold font-inter", text)}>
            %{trustScore}
          </span>
          <TooltipProvider>
            <Tooltip
              delayDuration={0}
              open={isTouchDevice ? isTooltipOpen : undefined}
              onOpenChange={handleTooltipChange}>
              <TooltipTrigger asChild>
                <button
                  aria-label="Trust Score Information"
                  className="cursor-pointer touch-manipulation hover:text-gray-600"
                  type="button"
                  onClick={handleButtonClick}>
                  <InfoIcon className="h-4 w-4 text-gray-400" />
                </button>
              </TooltipTrigger>
              <TooltipContent
                align="center"
                className="bg-[#1B242D] text-white font-inter text-[12px] sm:text-[13px] rounded-lg w-[200px] sm:w-[320px]"
                side="top"
                sideOffset={5}>
                <p className="text-center">
                  Trust score reflects Gurubase's confidence in this answer.
                  Always double-check references, as AI can make mistakes.
                </p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>

        <div
          aria-label={`Trust score ${trustScore}%`}
          aria-valuenow={trustScore}
          className="flex gap-[2px] ml-auto sm:ml-0"
          role="meter">
          {[...Array(10)].map((_, i) => (
            <div
              key={i}
              className={cn(
                "h-[17px] w-[10px] sm:h-[16px] sm:w-[12px] rounded-[4px] transition-colors",
                i < filledCells ? bg : "bg-gray-200"
              )}
            />
          ))}
        </div>
      </div>
    </Card>
  );
}
