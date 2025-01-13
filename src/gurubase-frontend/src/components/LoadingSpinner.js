const LoadingSpinner = () => {
  return (
    <div className="w-8 h-8 relative">
      <svg
        className="animate-[spin_1.5s_linear_infinite]"
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg">
        {/* 8 çizgi, her biri 45 derece açıyla */}
        <line
          x1="12"
          y1="2"
          x2="12"
          y2="6"
          stroke="#D1D5DB"
          strokeWidth="2"
          strokeLinecap="round"
        />
        <line
          x1="12"
          y1="18"
          x2="12"
          y2="22"
          stroke="#9CA3AF"
          strokeWidth="2"
          strokeLinecap="round"
        />

        <line
          x1="4.93"
          y1="4.93"
          x2="7.76"
          y2="7.76"
          stroke="#D1D5DB"
          strokeWidth="2"
          strokeLinecap="round"
        />
        <line
          x1="16.24"
          y1="16.24"
          x2="19.07"
          y2="19.07"
          stroke="#9CA3AF"
          strokeWidth="2"
          strokeLinecap="round"
        />

        <line
          x1="2"
          y1="12"
          x2="6"
          y2="12"
          stroke="#D1D5DB"
          strokeWidth="2"
          strokeLinecap="round"
        />
        <line
          x1="18"
          y1="12"
          x2="22"
          y2="12"
          stroke="#6B7280"
          strokeWidth="2"
          strokeLinecap="round"
        />

        <line
          x1="4.93"
          y1="19.07"
          x2="7.76"
          y2="16.24"
          stroke="#D1D5DB"
          strokeWidth="2"
          strokeLinecap="round"
        />
        <line
          x1="16.24"
          y1="7.76"
          x2="19.07"
          y2="4.93"
          stroke="#9CA3AF"
          strokeWidth="2"
          strokeLinecap="round"
        />
      </svg>
    </div>
  );
};

export default LoadingSpinner;
