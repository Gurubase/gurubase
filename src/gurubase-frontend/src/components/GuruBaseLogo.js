import clsx from "clsx";

import { getGuruTypeTextColor } from "@/components/Header/utils";
import useIsSmallScreen from "@/utils/hooks/useIsSmallScreen";

const GuruBaseLogo = ({ allGuruTypes, guruType, className }) => {
  const isSmallScreen = useIsSmallScreen();
  const hasCustomTextSize = className?.includes("text-");
  const textSize = hasCustomTextSize ? "" : "text-4xl";

  return (
    <header className="gap-2 self-stretch font-gilroy-semibold">
      <span>
        <span
          className={clsx(textSize, className)}
          style={{
            color: isSmallScreen
              ? getGuruTypeTextColor(guruType, allGuruTypes)
              : getGuruTypeTextColor(guruType, allGuruTypes)
          }}>
          Guru
        </span>
        <span className={clsx(textSize, "text-black-700", className)}>
          base
        </span>
      </span>
    </header>
  );
};

export default GuruBaseLogo;
