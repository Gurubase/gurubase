import QueryButton from "@/components/Content/QueryButton";
import { memo, useState, useEffect } from "react";
import { useAppDispatch } from "@/redux/hooks";
import { setResetMainForm } from "@/redux/slices/mainFormSlice";

const DefaultQuerySection = ({
  handleButtonClick,
  defaultQuestions,
  guruType
}) => {
  // get defaultQuestion from the backend and render them
  const dispatch = useAppDispatch();
  const [defaultQuestion, setDefaultQuestion] = useState(defaultQuestions);

  return (
    <nav className="flex xs:grid xs:grid-cols-1 flex-row gap-3  mt-4 text-sm font-medium text-center xs:text-start text-zinc-900 ">
      {Array.isArray(defaultQuestion) && defaultQuestion.length > 0
        ? defaultQuestion?.map((query, index) => (
            <QueryButton
              key={index}
              text={query?.question}
              guruType={guruType}
              slug={query?.slug}
              onClick={() => {
                handleButtonClick(query);
              }}
            />
          ))
        : null}
    </nav>
  );
};
// memoize DefaultQuerySection
export default memo(DefaultQuerySection);
