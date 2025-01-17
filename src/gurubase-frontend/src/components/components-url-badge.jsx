"use client";

import { Link } from "lucide-react";

import { Badge } from "@/components/ui/badge";

export function UrlBadgeJsx({ count }) {
  return (
    <Badge
      className="flex items-center gap-1 px-2 py-0.5 text-xs font-medium"
      variant="secondary">
      <Link className="w-3 h-3" prefetch={false} />
      {count}URL
    </Badge>
  );
}
