"use client";

import HistogramComponent from "./HistogramComponent";
import TimeSelectionComponent from "./TimeSelectionComponent";
import StatsCardComponent, { STAT_TYPES } from "./StatsCardComponent";
import TableComponent from "./TableComponent";
import {
  IntegrationHeader,
  IntegrationDivider
} from "../Integrations/IntegrationShared";
import { Icon } from "@iconify/react";
import { useState, useEffect } from "react";
import { useStatCards, useHistogram, useTableData } from "@/hooks/useAnalytics";
import { METRIC_TYPES } from "@/services/analyticsService";
import { useRouter, useSearchParams } from "next/navigation";

const HeaderTooltip = ({ text }) => {
  const [isHovered, setIsHovered] = useState(false);

  // Add useEffect to handle clicks outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      // Check if the click was outside the tooltip area
      if (isHovered && !event.target.closest(".tooltip-container")) {
        setIsHovered(false);
      }
    };

    // Add the event listener
    document.addEventListener("click", handleClickOutside);
    document.addEventListener("touchstart", handleClickOutside);

    // Clean up
    return () => {
      document.removeEventListener("click", handleClickOutside);
      document.removeEventListener("touchstart", handleClickOutside);
    };
  }, [isHovered]); // Only re-run if isHovered changes

  return (
    <div className="relative inline-block tooltip-container">
      <div
        className="ml-2 cursor-pointer"
        onMouseEnter={() => setIsHovered(true)}
        onClick={(e) => {
          e.stopPropagation(); // Prevent the document click from immediately closing it
          setIsHovered(!isHovered);
        }}
        onMouseLeave={() => setIsHovered(false)}>
        <Icon
          icon="solar:info-circle-linear"
          className="w-4 h-4 text-gray-400"
        />
        {isHovered && (
          <div
            className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 p-3 rounded-lg shadow-lg border bg-[#1B242D] text-white"
            style={{ minWidth: "200px", left: "calc(50% + 4px)" }}>
            {/* Triangle pointer */}
            <div
              className="absolute w-4 h-4 border-l border-t bg-[#1B242D]"
              style={{
                bottom: "-8px",
                left: "calc(50%)",
                transform: "translateX(-50%) rotate(225deg)",
                borderColor: "inherit"
              }}
            />
            <p className="text-center relative font-inter text-[12px] font-medium leading-normal px-2">
              {text}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

const MetricSection = ({
  title,
  tooltipText,
  metricType,
  interval,
  guruType
}) => {
  const [filterType, setFilterType] = useState("all");
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortOrder, setSortOrder] = useState("desc");
  const [selectedTimeRange, setSelectedTimeRange] = useState(null);

  // Add effect to reset time range when interval changes
  useEffect(() => {
    setSelectedTimeRange(null);
    setFilterType("all");
    setPage(1);
    setSearchQuery("");
    setSortOrder("desc");
  }, [interval]);

  const handleBarClick = (timeRange) => {
    setSelectedTimeRange(timeRange);
    // Reset filters when a bar is clicked
    setFilterType("all");
    setPage(1);
    setSearchQuery("");
    setSortOrder("desc");
  };

  const handleTimeRangeChange = (newTimeRange) => {
    setSelectedTimeRange(newTimeRange);
  };

  // Remove the useEffect for click outside handling

  const handleFilterChange = (newFilter) => {
    setFilterType(newFilter);
    setPage(1); // Reset page when filter changes
  };

  const handleSearch = (term) => {
    if (term !== searchQuery) {
      setSearchQuery(term);
      setPage(1);
    }
  };

  const { data: tableData, loading: tableLoading } = useTableData(
    guruType,
    metricType,
    interval,
    filterType,
    page,
    searchQuery,
    sortOrder,
    selectedTimeRange
  );

  const { data: histogramData, loading: histogramLoading } = useHistogram(
    guruType,
    metricType !== METRIC_TYPES.REFERENCED_SOURCES ? metricType : null,
    interval
  );

  return (
    <div>
      <div className="flex items-center mb-3">
        <h3 className="text-lg font-size-[17px] font-semibold">{title}</h3>
        <HeaderTooltip text={tooltipText} />
      </div>
      {metricType !== METRIC_TYPES.REFERENCED_SOURCES && (
        <HistogramComponent
          interval={interval}
          data={histogramData}
          isLoading={histogramLoading}
          onBarClick={handleBarClick}
        />
      )}
      <div className="mt-6"></div>
      <TableComponent
        metricType={metricType}
        data={tableData}
        onFilterChange={handleFilterChange}
        onPageChange={setPage}
        onSearch={handleSearch}
        currentFilter={filterType}
        currentPage={page}
        searchQuery={searchQuery}
        isLoading={tableLoading}
        guruType={guruType}
        interval={interval}
        onSortChange={setSortOrder}
        sortOrder={sortOrder}
        timeRange={selectedTimeRange}
        onTimeRangeChange={handleTimeRangeChange}
      />
    </div>
  );
};

const AnalyticsContent = ({ customGuru, initialInterval }) => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [interval, setInterval] = useState(initialInterval);
  const guruType = customGuru;
  const [metricType, setMetricType] = useState(METRIC_TYPES.QUESTIONS);
  const [currentFilter, setCurrentFilter] = useState("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortOrder, setSortOrder] = useState("desc");

  const handleIntervalChange = (newInterval) => {
    setInterval(newInterval);
    const params = new URLSearchParams(searchParams);
    params.set("interval", newInterval);
    router.push(`?${params.toString()}`, { scroll: false });
  };

  const { data: statCardsData, loading: statCardsLoading } = useStatCards(
    guruType,
    interval
  );

  // Only fetch histogram data if not referenced sources
  const { data: histogramData, loading: histogramLoading } = useHistogram(
    guruType,
    METRIC_TYPES.QUESTIONS,
    interval
  );

  const { data: tableData, loading: tableLoading } = useTableData(
    guruType,
    metricType,
    interval,
    currentFilter,
    currentPage,
    searchQuery,
    sortOrder
  );

  // Check if any data is loading
  const isLoading = statCardsLoading || histogramLoading || tableLoading;

  const handleFilterChange = (newFilter) => {
    setCurrentFilter(newFilter);
    setCurrentPage(1); // Reset page when filter changes
  };

  const handleSearch = (term) => {
    if (term !== searchQuery) {
      setSearchQuery(term);
      setCurrentPage(1);
    }
  };

  const handlePageChange = (newPage) => {
    setCurrentPage(newPage);
  };

  return (
    <>
      <IntegrationHeader text="Analytics" />
      <IntegrationDivider />
      <div className="grid grid-cols-4 p-6">
        <div className="col-span-3 guru-md:col-span-4 space-y-6">
          <div>
            <TimeSelectionComponent
              onPeriodChange={handleIntervalChange}
              defaultPeriod={interval}
              loading={isLoading}
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <StatsCardComponent
              title="Total Questions"
              value={statCardsData?.total_questions.value}
              percentageChange={
                statCardsData?.total_questions.percentage_change
              }
              statType={STAT_TYPES.HIGHER_BETTER}
              isLoading={statCardsLoading}
            />
            <StatsCardComponent
              title="Out of Context Questions"
              value={statCardsData?.out_of_context.value}
              percentageChange={statCardsData?.out_of_context.percentage_change}
              statType={STAT_TYPES.LOWER_BETTER}
              isLoading={statCardsLoading}
            />
            <StatsCardComponent
              title="Referenced Data Sources"
              value={statCardsData?.referenced_sources.value}
              percentageChange={
                statCardsData?.referenced_sources.percentage_change
              }
              statType={STAT_TYPES.NEUTRAL}
              isLoading={statCardsLoading}
            />
          </div>

          <MetricSection
            title="Questions"
            tooltipText="Total questions asked by users"
            metricType={METRIC_TYPES.QUESTIONS}
            interval={interval}
            guruType={guruType}
          />

          <MetricSection
            title="Unable to Answers"
            tooltipText="Questions without satisfactory answers"
            metricType={METRIC_TYPES.OUT_OF_CONTEXT}
            interval={interval}
            guruType={guruType}
          />

          <MetricSection
            title="Referenced Data Sources"
            tooltipText="Most referenced data sources"
            metricType={METRIC_TYPES.REFERENCED_SOURCES}
            interval={interval}
            guruType={guruType}
          />
        </div>

        <div className="block guru-md:hidden"></div>
      </div>
    </>
  );
};

export default AnalyticsContent;
