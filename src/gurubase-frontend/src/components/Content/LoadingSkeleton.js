import "react-loading-skeleton/dist/skeleton.css";

import Skeleton from "react-loading-skeleton";

const LoadingSkeleton = () => {
  return (
    <div className="flex flex-col justify-center p-6 xs:px-5 xs:max-w-full">
      <div className="flex flex-col justify-center p-px xs:max-w-full">
        <Skeleton count={5} />
      </div>
    </div>
  );
};

export default LoadingSkeleton;
