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

  const { data: histogramData, loading: histogramLoading } = useHistogram(
    guruType,
    metricType,
    interval
  );

  const { data: tableData, loading: tableLoading } = useTableData(
    guruType,
    metricType,
    interval,
    filterType,
    page
  );

  return (
    <div>
      <div className="flex items-center mb-3">
        <h3 className="text-lg font-size-[17px] font-semibold">{title}</h3>
        <HeaderTooltip text={tooltipText} />
      </div>
      <HistogramComponent
        interval={interval}
        data={histogramData}
        isLoading={histogramLoading}
      />
      <div className="mt-6"></div>
      <TableComponent
        data={tableData}
        onFilterChange={setFilterType}
        onPageChange={setPage}
        currentFilter={filterType}
        currentPage={page}
        isLoading={tableLoading}
      />
    </div>
  );
};

const AnalyticsContent = ({ customGuru }) => {
  const [interval, setInterval] = useState("today");
  const guruType = customGuru;

  const { data: statCardsData, loading: statCardsLoading } = useStatCards(
    guruType,
    interval
  );

  console.log("statCardsData", statCardsData);

  return (
    <>
      <IntegrationHeader text="Analytics" />
      <IntegrationDivider />
      <div className="grid grid-cols-4 px-6 pt-6">
        <div className="col-span-3 guru-md:col-span-4 space-y-8">
          <div>
            <TimeSelectionComponent
              onPeriodChange={setInterval}
              defaultPeriod={interval}
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
