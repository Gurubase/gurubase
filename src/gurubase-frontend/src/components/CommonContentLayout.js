import React from "react";

const CommonContentLayout = ({ children, sidebar }) => {
  return (
    <main className="z-10 flex justify-center items-center px-16 xs:px-0 w-full flex-grow xs:max-w-full polygon-fill">
      <div className="flex max-w-[1440px] w-full gap-4 h-full">
        {sidebar && <div className="h-full pt-10">{sidebar}</div>}
        <section className="flex-1 bg-white h-full xs:border-none border-l border-r border-solid border-neutral-200">
          <div className="flex h-full gap-6">
            <section className="flex flex-col flex-grow w-full h-full xs:ml-0">
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
