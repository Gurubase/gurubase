import React from 'react';
import { Button } from "@/components/ui/button";
import Image from "next/image";
import MapArrowUp from "@/assets/images/map-arrow-up.svg";
import clsx from "clsx";

const BingeMapMobileButton = ({
  activeNode,
  nodes,
  streamingStatus,
  handleNodeSelect
}) => {
  return (
    <div
      className="fixed left-1/2 transform -translate-x-1/2 md:hidden"
      style={{
        bottom: "calc(6vh + 24px)"
      }}>
      <Button
        className={clsx(
          "w-[90px] rounded-full text-white flex items-center justify-center",
          activeNode
            ? "bg-zinc-900 hover:bg-zinc-800 cursor-pointer"
            : "bg-zinc-500 hover:bg-zinc-500 cursor-not-allowed"
        )}
        onClick={() => {
          if (activeNode) {
            const selectedNode = nodes.find(
              (node) => node.id === activeNode
            );
            if (selectedNode?.slug) {
              handleNodeSelect(selectedNode);
            }
          }
        }}
        disabled={!activeNode || streamingStatus}>
        <Image
          src={MapArrowUp}
          alt="Map Arrow Up"
          width={13}
          height={13}
          className="mr-2"
        />
        <span>Open</span>
      </Button>
    </div>
  );
};

export default BingeMapMobileButton; 