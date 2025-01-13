import SourceCard from "./SourceCard";

function Sources({ resources, guruTypeText }) {
  if (!resources?.length) {
    return null;
  }

  return (
    <section className="flex flex-col px-8 pt-2 mb-16 guru-sm:px-5 ">
      <header className="flex flex-col justify-center w-full guru-sm:max-w-full">
        <p className="text-[1rem] font-semibold text-gray-800 guru-sm:max-w-full">
          Sources
        </p>
        <p className="mt-1 text-body2 font-normal text-gray-400 guru-sm:max-w-full guru-sm:text-body3">
          {guruTypeText} Guru leverages up-to-date information from the
          following sources to answer your questions.
        </p>
      </header>
      <div
        className={`guru-md:block guru-lg:block gap-4 items-center mt-6 w-full guru-sm:overflow-auto
        ${
          resources.length === 1
            ? "guru-sm:grid guru-sm:grid-cols-1 guru-md:grid guru-md:grid-cols-2 guru-lg:grid guru-lg:grid-cols-2"
            : resources.length === 2
              ? "guru-sm:grid guru-sm:grid-cols-1 guru-md:grid guru-md:grid-cols-2 guru-lg:grid guru-lg:grid-cols-2"
              : resources.length === 3
                ? "guru-sm:grid guru-sm:grid-cols-1 guru-md:grid guru-md:grid-cols-2 guru-lg:grid guru-lg:grid-cols-3 "
                : resources.length >= 4
                  ? "guru-sm:grid guru-sm:grid-cols-1 guru-md:grid guru-md:grid-cols-3 guru-lg:grid guru-lg:grid-cols-4"
                  : ""
        }
        `}>
        {resources.map((source, index) => (
          <SourceCard
            key={index + "source-card"}
            icon={source.icon}
            title={source.title}
            description={source.description}
            link={source.url}
          />
        ))}
      </div>
    </section>
  );
}

export default Sources;
