import React from 'react';

const BingeMapZoomControls = ({ scale, handleZoomIn, handleZoomOut, MIN_SCALE, MAX_SCALE }) => {
  return (
    <div className="absolute top-2 right-3 flex flex-col gap-2 z-[51]">
      <button
        onClick={handleZoomIn}
        className="p-2 bg-white rounded-full shadow-lg hover:bg-gray-50 transition-colors cursor-pointer"
        disabled={scale >= MAX_SCALE}
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
          <line x1="11" y1="8" x2="11" y2="14" />
          <line x1="8" y1="11" x2="14" y2="11" />
        </svg>
      </button>
      <button
        onClick={handleZoomOut}
        className="p-2 bg-white rounded-full shadow-lg hover:bg-gray-50 transition-colors cursor-pointer"
        disabled={scale <= MIN_SCALE}
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
          <line x1="8" y1="11" x2="14" y2="11" />
        </svg>
      </button>
    </div>
  );
};

export default BingeMapZoomControls; 