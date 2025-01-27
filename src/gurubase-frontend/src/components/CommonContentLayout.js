import React from "react";

const CommonContentLayout = ({ children, sidebar }) => {
  return (
    <main className="z-10 flex justify-center w-full flex-grow guru-sm:px-0 px-8">
      <div className="grid grid-flow-col guru-sm:grid-flow-row guru-sm:grid-cols-1 grid-cols-[253px_minmax(0,_1fr)] guru-sm:gap-0 gap-6 guru-sm:h-auto h-full w-full max-w-[1440px]">
        {sidebar}
        <section className="flex-1 bg-white h-full xs:border-none border-l border-r border-solid border-neutral-200">
          <div className="flex h-full">
            <section className="flex flex-col flex-grow w-full h-full">
              {/* Content goes here */}
              {children}
            </section>
          </div>
        </section>
      </div>
    </main>
  );
};

export default CommonContentLayout;
