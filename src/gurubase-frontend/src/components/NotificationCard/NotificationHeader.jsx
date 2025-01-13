import { Icon } from "@iconify/react";
import React from "react";

function NotificationHeader({ onClose }) {
  return (
    <header className="flex overflow-hidden gap-7 items-center p-4 w-full text-white bg-gray-800">
      <h2 className="flex-1 shrink self-stretch my-auto basis-0">
        Don&apos;t miss the latest updates about Gurubase
      </h2>
      <button
        onClick={onClose}
        className="object-contain shrink-0 self-stretch my-auto w-5 aspect-square bg-transparent border-none cursor-pointer"
        aria-label="Close notification">
        <Icon icon="ic:outline-close" className="w-5 h-5 text-white" />
      </button>
    </header>
  );
}

export default NotificationHeader;
