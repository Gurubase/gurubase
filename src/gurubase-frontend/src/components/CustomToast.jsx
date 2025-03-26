import { toast } from "sonner";
import { cn } from "@/lib/utils";

export const CustomToast = ({
  message,
  variant = "default",
  duration = 3000,
  action
}) => {
  let toastId;
  let visibleStartTime = null;
  let elapsed = 0;
  let interval;

  const startTracking = () => {
    visibleStartTime = Date.now();
    interval = setInterval(() => {
      if (document.visibilityState === "visible") {
        const now = Date.now();
        elapsed += now - visibleStartTime;
        visibleStartTime = now;

        if (elapsed >= duration) {
          toast.dismiss(toastId);
          cleanup();
        }
      }
    }, 100); // Check every 100ms
  };

  const stopTracking = () => {
    clearInterval(interval);
    visibleStartTime = null;
  };

  const handleVisibilityChange = () => {
    if (document.visibilityState === "visible") {
      visibleStartTime = Date.now();
      startTracking();
    } else {
      stopTracking();
    }
  };

  const cleanup = () => {
    stopTracking();
    document.removeEventListener("visibilitychange", handleVisibilityChange);
  };

  toastId = toast(message, {
    duration: Infinity,
    className: cn(
      "guru-toast",
      variant === "success" && "guru-toast-success",
      variant === "error" && "guru-toast-error",
      variant === "warning" && "guru-toast-warning",
      variant === "info" && "guru-toast-info"
    ),
    action: action && {
      label: action.label,
      onClick: action.onClick
    }
  });

  document.addEventListener("visibilitychange", handleVisibilityChange);
  if (document.visibilityState === "visible") {
    startTracking();
  }
};
