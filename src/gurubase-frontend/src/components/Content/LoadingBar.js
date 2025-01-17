import { useState, useEffect } from "react";

const LoadingBar = () => {
  const [loadingWidth, setLoadingWidth] = useState({ label: "1rem", value: 1 });

  useEffect(() => {
    const time = [1, 6.25, 12.5, 18.75];
    const interval = setInterval(() => {
      setLoadingWidth((prev) => {
        if (
          prev.value < 25 &&
          time.includes(time[time.indexOf(prev.value) + 1])
        ) {
          const next = time[time.indexOf(prev.value) + 1];
          return { label: `${next}rem`, value: next };
        }
        return prev;
      });
    }, 5000);
    return () => clearInterval(interval);
  }, []);
  return (
    <div className="flex flex-col justify-center items-start mt-6 max-w-full bg-gray-100 rounded-xl w-[300px]">
      <div
        className={`shrink-0 h-2 bg-anteon-blue rounded-[100px]`}
        style={{ width: loadingWidth.label }}
      />
    </div>
  );
};

export default LoadingBar;
