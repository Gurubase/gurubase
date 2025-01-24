import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export const IntegrationHeader = ({ name }) => (
  <h2 className="text-[#191919] font-inter text-[20px] font-medium p-6 pt-7">
    {name} Bot
  </h2>
);

export const IntegrationDivider = () => (
  <div className="h-[1px] bg-neutral-200" />
);

export const IntegrationIconContainer = ({ Icon, iconSize, children }) => (
  <div className="flex items-center gap-3">
    <div
      className={cn(
        "w-10 h-10 rounded-full flex items-center justify-center border border-neutral-200"
      )}>
      <Icon className={cn(iconSize, "text-white")} />
    </div>
    {children}
  </div>
);

export const IntegrationInfo = ({ name, description }) => (
  <div>
    <h3 className="font-medium">{name}</h3>
    <p className="text-sm text-muted-foreground">{description}</p>
  </div>
);

export const IntegrationError = ({ message }) => (
  <div className="text-red-500 bg-red-50 p-4 rounded-md">
    {message ||
      "There was an error during the integration process. Please try again or contact support if the issue persists."}
  </div>
);
