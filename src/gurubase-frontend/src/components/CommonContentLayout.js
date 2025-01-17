import React from "react";

const CommonContentLayout = (props) => {
  return (
    <main className="z-10 flex justify-center items-center px-16 xs:px-0 w-full flex-grow xs:max-w-full polygon-fill">
      <div className="flex justify-between w-full gap-4 h-full">
        <section className=" container mx-auto max-w-[1180px] bg-white h-full xs:border-none border-l border-r border-solid border-neutral-200">
          <section className="flex flex-col flex-grow w-full h-full xs:ml-0">
            {/* Content goes here */}
            {props.children}
          </section>
        </section>
      </div>
    </main>
  );
};

export default CommonContentLayout;
