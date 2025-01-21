import React from 'react';

const BingeMapNode = ({
  node,
  nodeSize,
  getNodeColor,
  areNodesDisabled,
  handleNodeClick,
  handleNodeHover
}) => {
  return (
    <g key={node.id}>
      <circle
        cx={node.x}
        cy={node.y}
        r={nodeSize}
        fill={getNodeColor(node)}
        className={`transition-colors duration-200 ${
          areNodesDisabled()
            ? "cursor-not-allowed"
            : "cursor-pointer"
        }`}
        onClick={() => {
          if (!areNodesDisabled()) {
            handleNodeClick(node.id);
          }
        }}
        onMouseEnter={() => {
          if (!areNodesDisabled()) {
            handleNodeHover(node.id);
          }
        }}
        onMouseLeave={() => {
          if (!areNodesDisabled()) {
            handleNodeHover(null);
          }
        }}
      />
    </g>
  );
};

export default BingeMapNode; 