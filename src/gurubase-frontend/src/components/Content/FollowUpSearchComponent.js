"use client";
import { useEffect, useRef } from "react";
import { useAppDispatch, useAppSelector } from "@/redux/hooks";
import { setInputQuery, setInputValue } from "@/redux/slices/mainFormSlice";

const FollowUpSearchComponent = ({
  inputId,
  onValueChange,
  sticky = false,
  sessionUserExists,
  onFocus,
  onBlur
}) => {
  const dispatch = useAppDispatch();
  const inputQuery = useAppSelector((state) => state.mainForm.inputQuery);
  const inputValue = useAppSelector((state) => state.mainForm.inputValue);

  const resetFocus = () => {
    // Remove focus from any active element
    if (document.activeElement instanceof HTMLElement) {
      document.activeElement.blur();
    }

    // Specifically remove focus from follow-up inputs and search
    document.querySelector(".aa-Input")?.blur();
    document.querySelectorAll("input").forEach((input) => input.blur());
  };

  const handleFocus = async () => {
    if (!(await sessionUserExists())) {
      resetFocus();
    } else {
      if (onFocus) {
        onFocus();
      }
    }
  };

  const handleInputChange = (e) => {
    const query = e.target.value;

    // Update Redux states
    dispatch(setInputValue(query));
    dispatch(setInputQuery(query));

    // Notify parent
    onValueChange?.(query);
  };

  useEffect(() => {
    if (sticky) {
      dispatch(setInputQuery(""));
      dispatch(setInputValue(""));
    }
  }, [sticky, dispatch]);

  return (
    <div id={inputId} className="flex-1 flex items-center h-full w-full">
      <input
        type="text"
        data-follow-up-input="bottom-search"
        className="w-full h-full bg-transparent outline-none text-sm placeholder:text-gray-400/50"
        placeholder="Ask follow-up"
        onChange={handleInputChange}
        value={inputValue || ""}
        onFocus={handleFocus}
        onBlur={onBlur}
      />
    </div>
  );
};

export default FollowUpSearchComponent;
