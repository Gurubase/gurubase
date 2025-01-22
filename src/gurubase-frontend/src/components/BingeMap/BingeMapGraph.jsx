import React from 'react';
import BingeMapNode from './BingeMapNode';

const BingeMapGraph = ({
  links,
  nodes,
  nodeSize,
  pan,
  scale,
  isDragging,
  getNodeColor,
  areNodesDisabled,
  handleNodeClick,
  handleNodeHover
}) => {
  return (
    <div className="w-full h-full overflow-hidden flex-1 min-h-0">
      <svg
        width="1000"
        height="1000"
        className="w-full h-full overflow-visible bg-transparent"
        style={{
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${scale})`,
          transition: isDragging ? "none" : "transform 0.3s ease-out",
          transformOrigin: "0 0"
        }}>
        <g>
          {/* Draw connection lines */}
          {links.map((link) => (
            <line
              key={link.id}
              x1={link.x1}
              y1={link.y1}
              x2={link.x2}
              y2={link.y2}
              stroke="hsl(var(--muted-foreground))"
              strokeWidth={Math.max(1, nodeSize / 12)}
              opacity={link.id.includes("streaming-temp") ? "0.3" : "0.5"}
              strokeDasharray={
                link.id.includes("streaming-temp") ? "5,5" : "none"
              }
            />
          ))}

          {/* Draw nodes */}
          {nodes.map((node) => (
            <BingeMapNode
              key={node.id}
              node={node}
              nodeSize={nodeSize}
              getNodeColor={getNodeColor}
              areNodesDisabled={areNodesDisabled}
              handleNodeClick={handleNodeClick}
              handleNodeHover={handleNodeHover}
            />
          ))}
        </g>
      </svg>
    </div>
  );
};

export default BingeMapGraph; 