import { toast } from "sonner";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

export const CustomToast = ({ message, variant = "default", duration = 3000, action }) => {
  toast(message, {
    duration: duration,
    className: cn(
      "guru-toast",
      variant === "success" && "guru-toast-success",
      variant === "error" && "guru-toast-error",
      variant === "warning" && "guru-toast-warning",
      variant === "info" && "guru-toast-info"
    ),
    action: action && {
      label: action.label,
      onClick: action.onClick,
    },
  });
};
