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
      <div className="space-y-8 px-6 pt-6">
        <div>
          <TimeSelectionComponent />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
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
          <h3 className="text-lg font-size-[17px] font-semibold mb-3">
            Questions
          </h3>
          <ChartExample1 />
          <div className="mt-6"></div>
          <TableComponent />
        </div>

        <div>
          <h3 className="text-lg font-size-[17px] font-semibold mb-3">
            Unable to Answers
          </h3>
          <ChartExample2 />
          <div className="mt-6"></div>
          <TableComponent />
        </div>

        <div>
          <h3 className="text-lg font-size-[17px] font-semibold mb-3">
            Popular Data Sources
          </h3>
          <LineChartComponent data={LineChartData} />
          <div className="mt-6"></div>
          <TableComponent />
        </div>
        <div className="mt-6 guru-md"></div>
      </div>
    </>
  );
};

export default AnalyticsContent;
