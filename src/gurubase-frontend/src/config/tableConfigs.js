import { Link, ExternalLink } from "lucide-react";
import { SolarFileTextBold, SolarVideoLibraryBold } from "@/components/Icons";
import { Icon } from "@iconify/react";
import { METRIC_TYPES } from "@/services/analyticsService";
import { Badge } from "@/components/ui/badge";
import { getColors } from "@/lib/trustScoreColors";

const sourceTypeIcons = {
  pdf: SolarFileTextBold,
  excel: SolarFileTextBold,
  youtube: SolarVideoLibraryBold,
  website: Link,
  jira: () => <Icon icon="simple-icons:jira" className="h-4 w-4" />,
  zendesk: () => <Icon icon="simple-icons:zendesk" className="h-4 w-4" />,
  codebase: () => <Icon icon="simple-icons:github" className="h-4 w-4" />,
  confluence: () => <Icon icon="simple-icons:confluence" className="h-4 w-4" />
};

export const tableConfigs = {
  [METRIC_TYPES.QUESTIONS]: {
    columns: [
      {
        key: "date",
        header: "Date",
        width: "w-[120px] md:w-[200px]",
        sortable: true
      },
      {
        key: "source",
        header: "Source",
        width: "w-[160px] flex-shrink-0",
        hideOnMobile: false,
        render: (item) => (
          <div className="flex items-center gap-2 ">{item.type}</div>
        )
      },
      {
        key: "title",
        header: "Question",
        width: "min-w-[300px] md:w-[400px] xl:w-[600px]",
        render: (item, { renderCellWithTooltip }) => (
          <a
            href={item.link}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 group hover:text-blue-600">
            <div className="cursor-pointer">
              {renderCellWithTooltip(item.truncated_title || item.title, {
                title: item.title
              })}
            </div>
            <ExternalLink className="h-3 w-3 flex-shrink-0 opacity-100" />
          </a>
        )
      },
      {
        key: "trust_score",
        header: "Trust Score",
        width: "w-[100px] flex-shrink-0",
        render: (item) => (
          <div className="flex items-center justify-center">
            <span
              className={
                item.trust_score
                  ? getColors(item.trust_score).text
                  : "text-gray-400"
              }>
              {item.trust_score ? `${item.trust_score}%` : "N/A"}
            </span>
          </div>
        )
      }
    ]
  },
  [METRIC_TYPES.OUT_OF_CONTEXT]: {
    columns: [
      {
        key: "date",
        header: "Date",
        width: "w-[160px] flex-shrink-0",
        minWidth: "80px",
        sortable: true
      },
      {
        key: "source",
        header: "Source",
        width: "w-[160px] flex-shrink-0",
        hideOnMobile: false,
        render: (item) => (
          <div className="flex items-center gap-2 ">{item.type}</div>
        )
      },
      {
        key: "title",
        header: "Question",
        width: "min-w-[300px] md:w-[400px] xl:w-[600px]",
        render: (item, { renderCellWithTooltip }) => (
          <a
            href={item.link}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 group">
            <div
              className={
                item.truncated_title && item.truncated_title !== item.title
                  ? "cursor-help"
                  : ""
              }>
              {renderCellWithTooltip(item.truncated_title || item.title, {
                title: item.title
              })}
            </div>
          </a>
        )
      }
    ]
  },
  [METRIC_TYPES.REFERENCED_SOURCES]: {
    columns: [
      {
        key: "date",
        header: "Date",
        width: "w-[160px] flex-shrink-0",
        minWidth: "80px"
      },
      {
        key: "type",
        header: "Type",
        width: "w-[160px] flex-shrink-0",
        hideOnMobile: false,
        render: (item) => {
          const IconComponent =
            sourceTypeIcons[item.type ? item.type.toLowerCase() : null];
          return IconComponent ? (
            <div className="flex items-center gap-2">
              <IconComponent className="h-4 w-4" />
              <span>{item.type}</span>
            </div>
          ) : null;
        }
      },
      {
        key: "title",
        header: "Title",
        width: "min-w-[300px] md:w-[400px] xl:w-[600px]",
        render: (item, { renderCellWithTooltip }) => (
          <a
            href={item.link}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 group hover:text-blue-600">
            <div className="cursor-pointer">
              {renderCellWithTooltip(item.truncated_title || item.title, {
                title: item.title
              })}
            </div>
            <ExternalLink className="h-3 w-3 flex-shrink-0 opacity-100" />
          </a>
        )
      },
      {
        key: "references",
        header: "Referenced",
        width: "w-[100px] flex-shrink-0",
        render: (item, { onReferenceClick }) => (
          <div className="flex items-center justify-center">
            <Badge
              variant="secondary"
              className="flex items-center rounded-full gap-1 px-2 py-1 text-xs font-medium cursor-pointer hover:bg-gray-50"
              text={
                <div className="flex items-center gap-1">
                  <Link className="h-3 w-3 text-blue-base" />
                  <span>{item.reference_count}</span>
                </div>
              }
              onClick={() => onReferenceClick?.(item)}
            />
          </div>
        )
      }
    ]
  },
  [METRIC_TYPES.QUESTIONS_LIST]: {
    columns: [
      {
        key: "date",
        header: "Date",
        width: "w-[120px] md:w-[200px]",
        sortable: true
      },
      {
        key: "source",
        header: "Source",
        width: "w-[140px]",
        hideOnMobile: false
      },
      {
        key: "title",
        header: "Question",
        width: "min-w-[300px] md:w-[400px] xl:w-[600px]",
        render: (item, { renderCellWithTooltip }) => (
          <a
            href={item.link}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 group hover:text-blue-600">
            <div className="cursor-pointer">
              {renderCellWithTooltip(item.truncated_title || item.title, {
                title: item.title
              })}
            </div>
            <ExternalLink className="h-3 w-3 flex-shrink-0 opacity-100" />
          </a>
        )
      },
      {
        key: "trust_score",
        header: "Trust Score",
        width: "w-[100px] flex-shrink-0",
        render: (item) => (
          <div className="flex items-center justify-center">
            <span
              className={
                item.trust_score
                  ? getColors(item.trust_score).text
                  : "text-gray-400"
              }>
              {item.trust_score ? `${item.trust_score}%` : "N/A"}
            </span>
          </div>
        )
      }
    ]
  }
};
