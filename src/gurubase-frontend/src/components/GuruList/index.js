import clsx from "clsx";
import { Plus } from "lucide-react";
import { useParams, usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import SearchBar from "@/components/OtherGurus/SearchBar";
import { Link } from "@/components/Link";
import { useAppDispatch } from "@/redux/hooks";
import { setBingeInfo, setResetMainForm } from "@/redux/slices/mainFormSlice";
import { GuruIconGetter } from "@/utils/guruIconGetter";
import { useAppNavigation } from "@/lib/navigation";

const GuruList = ({ allGuruTypes, title = "Find a Guru" }) => {
  const [guruTypes, setGuruTypes] = useState(allGuruTypes);
  const dispatch = useAppDispatch();
  const pathname = usePathname();
  const isMyGurusPage = pathname === "/my-gurus";
  const isSelfHosted = process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted";
  const navigation = useAppNavigation();

  const [filter, setFilter] = useState("");
  const [filteredGurus, setFilteredGurus] = useState(guruTypes);

  const { guruType } = useParams();

  useEffect(() => {
    dispatch(setBingeInfo({ treeData: null, bingeOutdated: false }));
  }, []);

  useEffect(() => {
    setFilteredGurus(guruTypes);
  }, [guruTypes]);

  useEffect(() => {
    if (filter.length > 2) {
      setFilteredGurus(
        guruTypes.filter((guru) =>
          guru?.name?.toLowerCase().includes(filter.toLowerCase())
        )
      );
    } else {
      setFilteredGurus(guruTypes);
    }
  }, [filter, guruTypes]);

  const handleGuruClick = (guru) => {
    dispatch(setResetMainForm());
    const url = isMyGurusPage ? `/guru/${guru.slug}` : `/g/${guru.slug}`;

    navigation.push(url);
  };

  return (
    <main className="flex justify-center items-center px-16 guru-sm:px-0 w-full flex-grow guru-sm:max-w-full polygon-fill">
      <section className="container mx-auto guru-md:max-w-[870px] guru-lg:max-w-[1180px] shadow-md bg-white h-full guru-sm:border-none border-l border-r border-solid border-neutral-200">
        <section
          className={clsx(
            "flex flex-col flex-grow w-full guru-sm:ml-0 px-6 py-4 guru-sm:py-6 border-b-gray-85 border-b-[0.5px] guru-sm:border-none",
            !guruType ? "guru-sm:bg-gray-25" : ""
          )}>
          <div className="flex flex-col w-full text-sm text-gray-400 gap-y-4">
            <p className="text-black-600 text-body font-medium guru-sm:hidden">
              {title}
            </p>
            <SearchBar
              filter={filter}
              placeholder="Search Guru"
              setFilter={setFilter}
            />
          </div>
        </section>
        <section className="flex flex-col flex-grow w-full guru-sm:ml-0 px-6 guru-sm:px-5 py-4">
          <div className="flex flex-wrap flex-1 w-full gap-x-2 gap-y-2">
            {isSelfHosted && (
              <Link
                aria-label="Create New Guru"
                className="flex flex-col justify-center text-center items-center cursor-pointer guru-xs:w-[calc(50%-4px)] w-[calc(25%-0.4rem)] pt-6 px-6 pb-3 h-32 border-gray-85 border-dashed border-2 rounded-xl text-body2 font-medium transition-colors"
                href="/guru/new-12hsh25ksh2"
                prefetch={false}
                role="button"
                tabIndex={0}>
                <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gray-50">
                  <Plus className="w-6 h-6 text-gray-600" />
                </div>
                <span className="mt-4 text-gray-600">Create New Guru</span>
              </Link>
            )}

            {filteredGurus &&
              filteredGurus?.map((guru) => {
                const href = isMyGurusPage
                  ? `/guru/${guru.slug}`
                  : `/g/${guru.slug}`;

                const iconUrl = isMyGurusPage ? guru.icon : guru.icon_url;

                return (
                  <Link
                    key={guru.slug}
                    className="flex flex-col justify-center text-center items-center cursor-pointer guru-xs:w-[calc(50%-4px)] w-[calc(25%-0.4rem)] pt-6 px-6 pb-3 h-32 border-gray-85 bg-gray-900 border-opacity-50 border rounded-xl text-body2 font-medium"
                    href={href}
                    prefetch={false}
                    onClick={(e) => {
                      e.preventDefault();
                      handleGuruClick(guru);
                    }}>
                    <GuruIconGetter
                      guru={guru?.slug}
                      guruName={guru?.name}
                      height={48}
                      iconUrl={iconUrl}
                      width={48}></GuruIconGetter>
                    <span className="mt-4 text-black-600">
                      {guru.name + " Guru"}
                    </span>
                  </Link>
                );
              })}
          </div>
        </section>
      </section>
    </main>
  );
};

export default GuruList;
