import { useAppDispatch } from "@/redux/hooks";
import { setActiveGuruName } from "@/redux/slices/mainFormSlice";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import Skeleton from "react-loading-skeleton";
import GuruItem from "./GuruItem";
import SearchBar from "./SearchBar";
import { Button } from "@/components/ui/button";
import { useAppNavigation } from "@/lib/navigation";

const OtherGurus = ({ isMobile, allGuruTypes }) => {
  const dispatch = useAppDispatch();
  const navigation = useAppNavigation();
  const [filter, setFilter] = useState("");
  const [filteredGurus, setFilteredGurus] = useState(allGuruTypes || []);
  const { guruType, slug } = useParams();
  const [activeGuru, setActiveGuru] = useState(null);
  const [isClient, setIsClient] = useState(false);
  const isSelfHosted = process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted";

  useEffect(() => {
    setIsClient(true);
  }, []);

  const findActiveGuru = (gurus, guruType) => {
    if (!gurus || !guruType) return null;
    return gurus.find(
      (guru) =>
        (guru && guru.slug && guru.slug.toLowerCase()) ===
        guruType.toLowerCase()
    );
  };

  const handleClickCreateGuru = () => {
    const url = isSelfHosted
      ? "/guru/new-12hsh25ksh2"
      : "/guru/create?source=/g/";

    window.open(url, "_blank", "noopener,noreferrer");
  };

  const activeGuruServerResponse = findActiveGuru(allGuruTypes, guruType);

  useEffect(() => {
    if (isClient && allGuruTypes?.length > 0) {
      // find active guru
      const activeGuru = findActiveGuru(allGuruTypes, guruType);
      setActiveGuru(activeGuru);
      // set Active Guru to redux store
      dispatch(setActiveGuruName(activeGuru?.name));
    }
  }, [allGuruTypes, guruType, dispatch, isClient]);

  useEffect(() => {
    if (filter.length > 1) {
      setFilteredGurus(
        allGuruTypes.filter((guru) =>
          guru?.name?.toLowerCase().includes(filter.toLowerCase())
        )
      );
    } else {
      setFilteredGurus(allGuruTypes);
    }
  }, [filter, allGuruTypes]);

  return (
    <>
      <section
        className={`flex flex-col items-start guru-md:justify-start h-min guru-md:h-[85vh] bg-white rounded-lg guru-sm:border-none border border-solid border-neutral-200 flex-1 guru-sm:max-w-full guru-sm:min-w-full guru-md:max-w-[280px] my-4 guru-sm:m-0 sticky guru-md:top-28 guru-lg:top-28 max-h-[calc(100vh-170px)] guru-md:max-h-full ${!isMobile && "guru-sm:hidden"}`}>
        <div className="flex z-0 flex-col pb-4 whitespace-nowrap bg-white rounded-t-xl border-solid border-b-[0.5px] border-b-neutral-200 shrink w-full">
          <div className="flex justify-between items-center px-3 py-5 w-full rounded-t-xl text-base font-medium bg-white border-solid border-b-[0.5px] border-b-neutral-200 min-h-[56px] text-zinc-900 guru-sm:hidden">
            <span>Gurus</span>
            <Button
              variant="outline"
              size="smButtonLgText"
              className="text-black hover:bg-gray-800 hover:text-white rounded-full"
              onClick={handleClickCreateGuru}>
              <div className="inline-flex items-center gap-2">
                <span>Create a Guru</span>
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 16 16"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg">
                  <path
                    fillRule="evenodd"
                    clipRule="evenodd"
                    d="M6 4.5C5.72386 4.5 5.5 4.27614 5.5 4C5.5 3.72386 5.72386 3.5 6 3.5H12C12.2761 3.5 12.5 3.72386 12.5 4V10C12.5 10.2761 12.2761 10.5 12 10.5C11.7239 10.5 11.5 10.2761 11.5 10V5.20711L4.35355 12.3536C4.15829 12.5488 3.84171 12.5488 3.64645 12.3536C3.45118 12.1583 3.45118 11.8417 3.64645 11.6464L10.7929 4.5H6Z"
                    fill="currentColor"
                  />
                </svg>
              </div>
            </Button>
          </div>
          <div className="flex flex-col px-3 mt-4 w-full text-sm text-gray-400">
            <SearchBar setFilter={setFilter} filter={filter} loading={false} />
          </div>
          <div className="flex justify-center items-center px-3 py-5 w-full rounded-t-xl bg-white border-solid border-b-[0.5px] border-b-neutral-200 min-h-[56px] text-zinc-900 hidden guru-sm:flex">
            <Button
              variant="outline"
              size="lgButtonLgText"
              className="text-black hover:bg-gray-800 hover:text-white rounded-full w-full"
              onClick={handleClickCreateGuru}>
              <div className="inline-flex items-center gap-2">
                <span>Create a Guru</span>
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 16 16"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg">
                  <path
                    fillRule="evenodd"
                    clipRule="evenodd"
                    d="M6 4.5C5.72386 4.5 5.5 4.27614 5.5 4C5.5 3.72386 5.72386 3.5 6 3.5H12C12.2761 3.5 12.5 3.72386 12.5 4V10C12.5 10.2761 12.2761 10.5 12 10.5C11.7239 10.5 11.5 10.2761 11.5 10V5.20711L4.35355 12.3536C4.15829 12.5488 3.84171 12.5488 3.64645 12.3536C3.45118 12.1583 3.45118 11.8417 3.64645 11.6464L10.7929 4.5H6Z"
                    fill="currentColor"
                  />
                </svg>
              </div>
            </Button>
          </div>
        </div>
        {false ? (
          <header className="flex flex-col w-full px-3">
            <Skeleton count={7} height={50} />
          </header>
        ) : (
          <div className="flex z-0 flex-col self-stretch w-full font-medium overflow-y-scroll featured-scrollbar">
            <header className="flex flex-col w-full">
              <div className="flex gap-2.5 justify-center items-center mt-2 px-3 w-full text-xs leading-none whitespace-nowrap text-neutral-400">
                <div className="flex-1 shrink self-stretch my-auto basis-0">
                  Active
                </div>
              </div>
              <div className="flex flex-col w-full text-sm text-zinc-900">
                <GuruItem
                  slug={activeGuruServerResponse?.slug || activeGuru?.slug}
                  text={activeGuruServerResponse?.name || activeGuru?.name}
                  icon={
                    activeGuruServerResponse?.icon_url || activeGuru?.icon_url
                  }
                />
              </div>
            </header>
            <div className="flex flex-col mt-4 w-full">
              <div className="flex-1 shrink gap-2.5 self-stretch px-3 w-full text-xs leading-none whitespace-nowrap text-neutral-400">
                Gurus
              </div>
              <nav className="flex flex-col mt-2 w-full text-sm text-zinc-900">
                {filteredGurus
                  ?.filter(
                    (guru) =>
                      guru?.name?.toLowerCase() !== guruType?.toLowerCase()
                  )
                  .map((guru, index) => (
                    <GuruItem
                      key={index}
                      slug={guru?.slug}
                      text={guru?.name}
                      icon={guru?.icon_url}
                    />
                  ))}
              </nav>
            </div>
          </div>
        )}
      </section>
    </>
  );
};

export default OtherGurus;
