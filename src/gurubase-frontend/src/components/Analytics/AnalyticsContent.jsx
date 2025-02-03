import BarChartComponent from "./BarChartComponent";
import LineChartComponent from "./LineChartComponent";
import TimeSelectionComponent from "./TimeSelectionComponent";
import { generateBarChartData } from "./GenerateBarChartData";
import StatsCardComponent from "./StatsCardComponent";
import TableComponent from "./TableComponent";
import {
  IntegrationHeader,
  IntegrationDivider
} from "../Integrations/IntegrationShared";
import { Icon } from "@iconify/react";
import { useState, useEffect } from "react";

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

const ChartExamples = () => {
  return (
    <div className="space-y-8">
      <div>
        {/* <h3 className="text-lg font-medium mb-2">Today (Hourly)</h3> */}
        <BarChartComponent
          interval="today"
          data={generateBarChartData("today")}
        />
      </div>

      {/* <div>
        <h3 className="text-lg font-medium mb-2">Last 7 Days</h3>
        <BarChartComponent interval="7d" data={generateBarChartData("7d")} />
      </div>

      <div>
        <h3 className="text-lg font-medium mb-2">Last 30 Days</h3>
        <BarChartComponent interval="30d" data={generateBarChartData("30d")} />
      </div> */}
    </div>
  );
};

const ChartExample1 = () => {
  return (
    <div className="space-y-8">
      <div>
        <BarChartComponent
          interval="today"
          data={generateBarChartData("today")}
        />
      </div>
    </div>
  );
};

const ChartExample2 = () => {
  return (
    <div className="space-y-8">
      <BarChartComponent interval="7d" data={generateBarChartData("7d")} />
    </div>
  );
};

const LineChartData = [
  {
    text: "I want to create pods with custom ordinal index in stateful set",
    value: 7602
  },
  {
    text: "I want to create pods with custom ordinal index in stateful set",
    value: 500
  },
  {
    text: "I want to create pods with custom ordinal index in stateful set",
    value: 200
  },
  {
    text: "I want to create pods with custom ordinal index in stateful set",
    value: 180
  },
  {
    text: "I want to create pods with custom ordinal index in stateful set",
    value: 175
  },
  {
    text: "I want to create pods with custom ordinal index in stateful set",
    value: 160
  },
  { text: "Others", value: 750 },
  {
    text: "I want to create pods with custom ordinal index in stateful set",
    value: 100
  }
];

const AnalyticsContent = () => {
  return (
    <>
      <IntegrationHeader text="Analytics" />
      <IntegrationDivider />
      <div className="grid grid-cols-4 px-6 pt-6">
        <div className="col-span-3 guru-md:col-span-4 space-y-8">
          <div>
            <TimeSelectionComponent />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <StatsCardComponent
              title="Total Questions"
              value={100}
              percentageChange={20}
            />
            <StatsCardComponent
              title="Out of Context Questions"
              value={23}
              percentageChange={-20}
            />
            <StatsCardComponent
              title="Popular Data Sources"
              value={56}
              percentageChange={0}
            />
          </div>
          <div>
            <div className="flex items-center mb-3">
              <h3 className="text-lg font-size-[17px] font-semibold">
                Questions
              </h3>
              <HeaderTooltip text="Total questions asked by users" />
            </div>
            <ChartExample1 />
            <div className="mt-6"></div>
            <TableComponent />
          </div>

          <div>
            <div className="flex items-center mb-3">
              <h3 className="text-lg font-size-[17px] font-semibold">
                Unable to Answers
              </h3>
              <HeaderTooltip text="Questions without satisfactory answers" />
            </div>
            <ChartExample2 />
            <div className="mt-6"></div>
            <TableComponent />
          </div>

          <div>
            <div className="flex items-center mb-3">
              <h3 className="text-lg font-size-[17px] font-semibold">
                Popular Data Sources
              </h3>
              <HeaderTooltip text="Most accessed data sources" />
            </div>
            <div className="mt-6"></div>
            <TableComponent />
          </div>
        </div>

        {/* Fourth Column - Empty */}
        <div className="block guru-md:hidden"></div>
      </div>
    </>
  );
};

export default AnalyticsContent;
