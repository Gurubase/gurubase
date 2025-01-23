import React from 'react';

const BingeMapTooltip = ({ node, scale, pan, nodes }) => {
  if (!node) return null;

  const nodeY = node.y * scale + pan.y;
  const nodeX = node.x * scale + pan.x;

  const isRootNode = !nodes.some((n) =>
    n.children?.some((child) => child.id === node.id)
  );

  const tooltipOnBottom = !isRootNode;

  return (
    <div
      className="absolute rounded-lg shadow-lg p-3 border md:bg-[#1B242D] md:text-white bg-background"
      style={{
        left: `${nodeX}px`,
        top: `${nodeY + (tooltipOnBottom ? -24 : 24)}px`,
        transform: `translate(-50%, ${tooltipOnBottom ? "-100%" : "0"}) scale(${scale})`,
        maxWidth: "300px",
        minWidth: "100px",
        width: "max-content",
        transformOrigin: tooltipOnBottom
          ? "bottom center"
          : "top center",
        zIndex: 50
      }}>
      {/* Triangle pointer */}
      <div
        className="absolute w-4 h-4 border-l border-t md:bg-[#1B242D] bg-background"
        style={{
          [tooltipOnBottom ? "bottom" : "top"]: "-8px",
          left: "50%",
          transform: `translateX(-50%) rotate(${tooltipOnBottom ? "225deg" : "45deg"})`,
          borderColor: "inherit"
        }}
      />
      <p
        className="text-center relative font-inter px-2"
        style={{
          fontSize: "12px",
          fontWeight: 500,
          lineHeight: "normal"
        }}>
        {node.text}
      </p>
    </div>
  );
};

export default BingeMapTooltip; 