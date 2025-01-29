"use client";
import { ArrowDown, ChevronRight } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { getBingeHistory } from "@/app/actions";
import { SolarMagniferOutline } from "@/components/Icons";
import LoadingSpinner from "@/components/LoadingSpinner";
import { useAppDispatch } from "@/redux/hooks";
import {
  resetErrors,
  setBingeId,
  setBingeInfo
} from "@/redux/slices/mainFormSlice";
import { formatDate } from "@/utils/dateUtils";

const BingeHistory = ({ guruTypes }) => {
  const [history, setHistory] = useState({
    today: [],
    last_week: [],
    older: []
  });
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const timeoutRef = useRef(null);

  const getGuruIcon = (guruType) => {
    const guru = guruTypes.find((g) => g.slug === guruType);

    return guru?.icon_url || "/default-guru-icon.png";
  };

  useEffect(() => {
    dispatch(setBingeInfo({ treeData: null, bingeOutdated: false }));
  }, []);

  const dispatch = useAppDispatch();

  dispatch(resetErrors());

  const loadHistory = useCallback(async (pageNum, query = "") => {
    try {
      setLoading(true);
      const data = await getBingeHistory(pageNum, query);

      if (pageNum === 1) {
        setHistory({
          today: data.today,
          last_week: data.last_week,
          older: data.older
        });
      } else {
        setHistory((prev) => ({
          today: [...prev.today, ...data.today],
          last_week: [...prev.last_week, ...data.last_week],
          older: [...prev.older, ...data.older]
        }));
      }

      setHasMore(data.has_more);
    } catch (error) {
      // console.error("Error fetching binge history:", error);
      setHasMore(false);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    if (page === 1) {
      loadHistory(1);
    }
    setPage(2);
    dispatch(setBingeId(null));
  }, []);

  const handleLoadMore = () => {
    if (loading || !hasMore) return;
    loadHistory(page, searchQuery);
    setPage((prev) => prev + 1);
  };

  const handleSearchChange = (e) => {
    setSearchQuery(e.target.value);
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    loadHistory(1, searchQuery);
    setPage(2);
  };

  const renderHistorySection = (title, items) => {
    if (!items?.length) return null;

    return (
      <div className="mb-4">
        <h2 className="text-sm font-medium mb-3">{title}</h2>
        <div className="space-y-3">
          {items.map((item, index) => (
            <Link
              key={item.id}
              className="flex items-center gap-3 rounded-lg border bg-white p-4 shadow-sm transition-colors hover:bg-gray-50"
              href={`/g/${item.guru_type_slug}/${item.root_question_slug}/binge/${item.id}?question_slug=${item.root_question_slug}`}>
              <Image
                alt="Guru Icon"
                className="rounded-full"
                height={24}
                src={getGuruIcon(item.guru_type_slug)}
                width={24}
              />
              <div className="flex flex-col gap-0.5">
                <h2 className="text-sm font-medium text-black whitespace-normal break-words">
                  {item.root_question_name}
                </h2>
                <p className="text-xs text-gray-500">
                  {formatDate(item.last_used)}
                </p>
              </div>
              <ChevronRight className="ml-auto h-4 w-4 text-gray-400" />
            </Link>
          ))}
        </div>
      </div>
    );
  };

  return (
    <main className="flex justify-center items-center px-16 guru-sm:px-0 w-full flex-grow guru-sm:max-w-full polygon-fill">
      <div className="flex max-w-[1440px] w-full gap-4 h-full">
        <div className="grid guru-lg:grid-cols-2 grid-cols-1 h-full">
          <div className="bg-white shadow-md guru-sm:border-none border-l border-r guru-lg:border-r-0 border-solid border-neutral-200">
            <div className="block guru-sm:hidden border-r border-gray-200">
              <div className="h-full polygon-fill bg-repeat opacity-[0.02]" />
            </div>

            <section className="bg-white border-gray-200">
              <div className="p-6">
                <h1 className="text-[20px] font-semibold text-[#191919] font-inter mb-2">
                  Binge History
                </h1>
                <p className="text-[14px] font-normal text-[#6D6D6D] font-inter mb-4">
                  Binge History lets you see all your history interactions in
                  one place and continue right where you left off!
                </p>

                <form className="mb-8" onSubmit={handleSearchSubmit}>
                  <div className="flex gap-2 items-center px-3 py-3.5 w-full bg-white rounded-lg border border-solid border-neutral-200 text-base">
                    <label className="sr-only" htmlFor="searchInput">
                      Search in history
                    </label>

                    <SolarMagniferOutline
                      className="text-anteon-orange"
                      height={16}
                      width={16}
                    />
                    <input
                      className="flex-1 shrink self-stretch w-full my-auto basis-0 text-ellipsis bg-transparent border-none outline-none"
                      disabled={loading}
                      id="searchInput"
                      placeholder="Search in history..."
                      type="search"
                      value={searchQuery}
                      onChange={handleSearchChange}
                    />
                  </div>
                </form>

                {renderHistorySection("Today", history.today)}
                {renderHistorySection("Last Week", history.last_week)}
                {renderHistorySection("Older", history.older)}

                {hasMore ? (
                  loading ? (
                    <div className="flex justify-center mt-8 mb-6">
                      <LoadingSpinner />
                    </div>
                  ) : (
                    <div className="flex justify-center mt-4 mb-6">
                      <button
                        className="flex items-center gap-2 px-4 py-2 text-[#191919] border border-[#E5E7EB] rounded-lg hover:bg-gray-50 transition-colors"
                        onClick={handleLoadMore}>
                        Load More
                        <ArrowDown size={20} />
                      </button>
                    </div>
                  )
                ) : null}
              </div>
            </section>
          </div>

          {/* Right column - Empty space on large screens */}
          <div className="hidden guru-lg:block bg-white guru-sm:border-none border-r border-solid border-neutral-200">
            {/* You can add content here for the right column if needed */}
          </div>
        </div>
      </div>
    </main>
  );
};

export default BingeHistory;
