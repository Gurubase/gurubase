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
import { HeaderTooltip } from "@/components/ui/header-tooltip";
import { exportAnalytics } from "@/utils/clientActions";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";

const MetricSection = ({
  title,
  tooltipText,
  metricType,
  interval,
  guruType,
  onFilterChange
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

  const handleFilterChange = (newFilter) => {
    setFilterType(newFilter);
    setPage(1); // Reset page when filter changes
    onFilterChange(newFilter);
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
        <>
          <HistogramComponent
            interval={interval}
            data={histogramData}
            isLoading={histogramLoading}
            onBarClick={handleBarClick}
            timeRange={selectedTimeRange}
          />
          <div className="mt-6"></div>
        </>
      )}
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

const AnalyticsContent = ({ guruData, initialInterval }) => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [interval, setInterval] = useState(initialInterval);
  const guruType = guruData?.slug;
  const [searchQuery, setSearchQuery] = useState("");
  const [isExporting, setIsExporting] = useState(false);
  const [metricFilters, setMetricFilters] = useState({
    questions: "all",
    out_of_context: "all",
    referenced_sources: "all"
  });

  const handleExport = async (exportType) => {
    try {
      setIsExporting(true);
      await exportAnalytics(guruType, interval, metricFilters, exportType);
    } catch (error) {
      console.error("Export failed:", error);
    } finally {
      setIsExporting(false);
    }
  };

  useEffect(() => {
    console.log(metricFilters);
  }, [metricFilters]);

  const handleFilterChange = (metricType, filterType) => {
    setMetricFilters((prev) => ({
      ...prev,
      [metricType]: filterType
    }));
  };

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

  // Check if any data is loading
  const isLoading = statCardsLoading;

  return (
    <>
      <IntegrationHeader text="Analytics" />
      <IntegrationDivider />
      <div className="grid grid-cols-4 p-6">
        <div className="col-span-3 guru-md:col-span-4 space-y-6">
          <div className="flex justify-between items-center">
            <TimeSelectionComponent
              onPeriodChange={handleIntervalChange}
              defaultPeriod={interval}
              loading={isLoading}
            />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" disabled={isExporting}>
                  {isExporting ? "Exporting..." : "Export"}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem onClick={() => handleExport("xlsx")}>
                  Export as Excel
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
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
            tooltipText="Total questions asked by users."
            metricType={METRIC_TYPES.QUESTIONS}
            interval={interval}
            guruType={guruType}
            onFilterChange={(filterType) =>
              handleFilterChange("questions", filterType)
            }
          />

          <MetricSection
            title="Unable to Answers"
            tooltipText="Questions that cannot be answered. The reason could be that the question is unrelated to the Guru, or the Guru's data source is insufficient to generate an answer."
            metricType={METRIC_TYPES.OUT_OF_CONTEXT}
            interval={interval}
            guruType={guruType}
            onFilterChange={(filterType) =>
              handleFilterChange("out_of_context", filterType)
            }
          />

          <MetricSection
            title="Referenced Data Sources"
            tooltipText="Most referenced data sources."
            metricType={METRIC_TYPES.REFERENCED_SOURCES}
            interval={interval}
            guruType={guruType}
            onFilterChange={(filterType) =>
              handleFilterChange("referenced_sources", filterType)
            }
          />
        </div>

        <div className="block guru-md:hidden"></div>
      </div>
    </>
  );
};

export default AnalyticsContent;
