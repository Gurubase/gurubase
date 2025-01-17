import { Icon } from "@iconify/react";
import clsx from "clsx";
import React from "react";

function NotificationItem({ icon, text, index, link }) {
  return (
    <div
      className="flex overflow-hidden gap-2 items-center p-4 w-full bg-white border-b border-solid border-b-neutral-200"
      onClick={() => window.open(link, "_blank")}>
      <Icon
        icon={icon}
        className={clsx(
          "object-contain shrink-0 self-stretch my-auto w-5 h-5 aspect-square",
          index === 1 ? "text-anteon-discord" : "text-black-600"
        )}
      />
      <div
        className={`flex-1 shrink self-stretch my-auto basis-0 hover:underline cursor-pointer`}>
        {text}
      </div>
      <Icon
        icon={"solar:arrow-right-up-outline"}
        className="object-contain shrink-0 self-stretch my-auto w-5 h-5 aspect-square cursor-pointer"
      />
    </div>
  );
}

export default NotificationItem;
