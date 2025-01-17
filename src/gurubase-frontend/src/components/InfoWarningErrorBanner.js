import { Icon } from "@iconify/react";
import { clsx } from "clsx";
import { useState } from "react";

const InfoWarningErrorBanner = (props) => {
  const { actionButtons, type } = props;
  const [isDismissed, setIsDismissed] = useState(false);

  if (isDismissed) {
    return null;
  }

  const getIconText = (type) => {
    switch (type) {
      case "info":
        return "solar:info-circle-bold";
      case "success":
        return "solar:check-circle-bold";
      case "error":
        return "solar:close-circle-bold";
      case "warning":
        return "solar:shield-warning-bold";
      default:
        return "solar:info-circle-bold";
    }
  };

  const getIconColor = (type) => {
    switch (type) {
      case "info":
        return "text-blue-base";
      case "success":
        return "text-success-base";
      case "error":
        return "text-error-base";
      case "warning":
        return "text-warning-base";
      default:
        return "text-blue-base";
    }
  };

  return (
    <div className={`w-full px-5 xs:px-4 mt-4`}>
      <section
        className={clsx(
          "flex justify-between align-items-center p-3 xs:px-2 text-body1  border border-solid border-neutral-200 rounded-[1000px] xs:rounded-[20px] ",
          type === "info" && "bg-blue-50 border border-1 border-blue-base",
          type === "success" &&
            "bg-success-50 border border-1 border-success-base",
          type === "error" && "bg-error-50 border border-1 border-error-base",
          type === "warning" &&
            "bg-warning-50 border border-1 border-warning-base"
        )}>
        <div className="flex align-middle gap-2 xs:gap-1 flex-nowrap">
          <Icon
            icon={getIconText(type)}
            width="1.5rem"
            height="1.5rem"
            className={clsx("icon", getIconColor(type), "xs:w-16")}
          />

          <div className="message">{props.children}</div>
        </div>
        {actionButtons && (
          <div className="actionWrapper">
            {actionButtons.dismissButton && (
              <button
                aria-label="icon with later"
                onClick={() => setIsDismissed(true)}
                className="dismissButton">
                Later
              </button>
            )}
            {actionButtons.applyButton && (
              <button
                aria-label="icon with apply"
                onClick={actionButtons.applyButton.onClick}
                className="startButton">
                {actionButtons.applyButton.children}
              </button>
            )}
          </div>
        )}
      </section>
    </div>
  );
};

export default InfoWarningErrorBanner;
