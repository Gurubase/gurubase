import React from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Clock } from "lucide-react";

// Component to indicate potentially long update times
export const LongUpdatesIndicator = () => {
  return (
    <Alert className="w-full">
      <div className="flex items-center gap-2">
        <Clock className="h-4 w-4" />
        <AlertDescription>
          Updates can take seconds to minutes, depending on the size of the data
          sources. You can leave and return to check later.
        </AlertDescription>
      </div>
    </Alert>
  );
};
