import dynamic from "next/dynamic";

import { SolarInfoCircleBold } from "@/components/Icons";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from "@/components/ui/tooltip";

// Add this dynamic import for MonacoEditor
const MonacoEditor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false
});

const editorOptions = {
  minimap: { enabled: false },
  lineNumbers: "on",
  lineNumbersMinChars: 2,
  scrollBeyondLastLine: true,
  wordWrap: "on",
  automaticLayout: true,
  mouseWheelZoom: false,
  pinchZoom: false,
  scrollbar: {
    vertical: "hidden",
    horizontal: "hidden",
    useShadows: false
  },
  overviewRulerBorder: false,
  hideCursorInOverviewRuler: true,
  contextmenu: false,
  quickSuggestions: false,
  suggestOnTriggerCharacters: false,
  snippetSuggestions: "none",
  wordBasedSuggestions: false,
  parameterHints: {
    enabled: false
  },
  folding: false,
  renderLineHighlight: "none",
  matchBrackets: "never",
  selectionHighlight: false,
  occurrencesHighlight: false,
  links: false,
  colorDecorators: false,
  hover: {
    enabled: false
  },
  find: {
    addExtraSpaceOnTop: false,
    autoFindInSelection: "never",
    seedSearchStringFromSelection: false
  },
  lineDecorationsWidth: 15,
  glyphMargin: false
};

const MonacoUrlEditor = ({
  title,
  tooltipText,
  value,
  onChange,
  placeholder
}) => {
  return (
    <>
      <div className="flex items-center space-x-1 mb-3">
        <h3 className="text-sm font-semibold">{title}</h3>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div>
                <SolarInfoCircleBold className="h-4 w-4 text-gray-200" />
              </div>
            </TooltipTrigger>
            <TooltipContent>
              <p>{tooltipText}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
      <div
        className={`border rounded-[8px] p-1 h-[calc(100vh-170px)] relative`}>
        <MonacoEditor
          height="100%"
          language="plaintext"
          options={editorOptions}
          theme="vs-light"
          value={value}
          onChange={onChange}
        />
        {!value && (
          <div className="monaco-placeholder absolute top-0 left-0 right-0 bottom-0 pointer-events-none">
            <div className="pl-[35px] pt-[3px] text-gray-400 text-[13px]">
              {placeholder}
            </div>
          </div>
        )}
      </div>
    </>
  );
};

export default MonacoUrlEditor;
