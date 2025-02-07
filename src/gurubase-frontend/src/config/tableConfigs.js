import { Link, ExternalLink } from "lucide-react";
import { SolarFileTextBold, SolarVideoLibraryBold } from "@/components/Icons";
import { Icon } from "@iconify/react";
import { METRIC_TYPES } from "@/services/analyticsService";
import { Badge } from "@/components/ui/badge";

const sourceTypeIcons = {
  pdf: SolarFileTextBold,
  youtube: SolarVideoLibraryBold,
  website: Link,
  codebase: () => <Icon icon="simple-icons:github" className="h-4 w-4" />
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
          const IconComponent = sourceTypeIcons[item.type?.toLowerCase()];
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
        render: (item) => (
          <a
            href={item.link}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 group hover:text-blue-600">
            <div className="">{item.title}</div>
            <ExternalLink className="h-3 w-3 flex-shrink-0 opacity-100" />
          </a>
        )
      },
      {
        key: "references",
        header: "Referenced",
        width: "w-[100px] flex-shrink-0",
        render: (item, { onReferenceClick }) => (
          <Badge
            iconColor="text-gray-500"
            text={
              <div className="flex items-center gap-1">
                <Link className="h-3 w-3 text-gray-500" />
                <span>{item.reference_count}</span>
              </div>
            }
            variant="secondary"
            className="cursor-pointer hover:bg-gray-100"
            onClick={() => onReferenceClick?.(item)}
          />
        )
      }
    ]
  }
};
