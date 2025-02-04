import clsx from "clsx";
import Image from "next/image";
import { useEffect } from "react";

import ZoomIn from "@/assets/images/zoom-in-scale-up.svg";
import { useAppDispatch, useAppSelector } from "@/redux/hooks";
import {
  setInputValue,
  setInvalidAnswer,
  setMobileInputFocused
} from "@/redux/slices/mainFormSlice";

const QueryInput = ({
  onSubmit,
  guruType,
  setContentWrapperWidth,
  setContentWrapperLeft,
  guruTypePromptName
}) => {
  const dispatch = useAppDispatch();
  const inputValue = useAppSelector((state) => state.mainForm.inputValue);
  const isLoading = useAppSelector((state) => state.mainForm.isLoading);

  const panelHintsListed = useAppSelector(
    (state) => state.mainForm.panelHintsListed
  );

  // if scroll y is greater than 100px then fixed the search bar to top of the page else not fixed to top of the page write a function to handle this and assign it to the scroll event listener and return the cleanup function to remove the event listener and return tailwind css classes to the form element to fixed to top of the page or not fixed to top of the page
  const handleScroll = () => {
    // don't make the search bar fixed if the user is on the guru type home page
    const slug = window.location.pathname.split("/").pop();

    if (slug.toLowerCase() === guruType.toLowerCase()) {
      return;
    }

    if (typeof window !== "undefined") {
      const contentWrapper = document?.querySelector(".content-wrapper");

      setContentWrapperWidth(contentWrapper?.clientWidth + "px");
      setContentWrapperLeft(
        // get the left position of the content wrapper
        contentWrapper?.getBoundingClientRect().left + "px"
      );
    }
    const searchElement = document.querySelector(".fixed-search");
    const fixedClass = `fixed top-0 right-0 z-10 container flex-1 guru-sm:h-[6rem] guru-sm:flex guru-sm:justify-center guru-sm:items-end guru-sm:pb-4 guru-sm:px-2`;

    if (window.scrollY >= 30 && window.innerWidth <= 915) {
      // Use the state to add or remove classes
      searchElement?.classList.add(...fixedClass.split(" "));
    } else {
      searchElement?.classList.remove(...fixedClass.split(" "));
    }
  };

  useEffect(() => {
    window.addEventListener("scroll", handleScroll);
    window.addEventListener("resize", handleScroll);

    return () => {
      window.removeEventListener("scroll", handleScroll);
      window.removeEventListener("resize", handleScroll);
    };
  }, []);

  const handleKeyPress = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      // Unfocus input on submit
      e.target.blur();
      onSubmit(e);
    }
  };

  const handleMobileInputFocus = () => {
    if (window.innerWidth <= 915) {
      dispatch(setInvalidAnswer(null));
      dispatch(setMobileInputFocused(true));
      document.body.style.overflow = "hidden";

      return;
    }
    dispatch(setMobileInputFocused(false));
  };

  const handleMobileInputBlur = () => {
    dispatch(setMobileInputFocused(false));
    document.body.style.overflow = "auto";
  };

  const handleInputChange = (e) => {
    dispatch(setInputValue(e.target.value));
  };

  // Update form onSubmit handler
  const handleFormSubmit = (e) => {
    e.preventDefault();
    // Unfocus input on submit
    if (document.activeElement instanceof HTMLElement) {
      document.activeElement.blur();
    }
    onSubmit(e);
  };

  return (
    <form
      className={clsx(
        "flex gap-2 guru-sm:gap-1 items-center px-3 guru-sm:px-4 max-h-16 bg-gray-900 guru-sm:flex-wrap",
        panelHintsListed ? "rounded-t-[30px]" : "rounded-[40px]"
      )}
      onSubmit={handleFormSubmit}>
      <label className="sr-only" htmlFor="queryInput">
        Ask anything about {guruType}
      </label>
      <button
        aria-label="icon with zoom in"
        className="shrink-0 self-stretch w-8 aspect-square z-10"
        disabled={isLoading}
        type="submit">
        <Image
          alt="Icon"
          className={clsx(
            "shrink-0 self-stretch my-auto aspect-square",
            isLoading && "opacity-50"
          )}
          height={24}
          loading="lazy"
          src={ZoomIn}
          width={24}
        />
      </button>
      <input
        className={clsx(
          "flex-1 bg-transparent placeholder-gray-400 focus:outline-none py-4 text-base",
          isLoading && "cursor-not-allowed opacity-50"
        )}
        disabled={isLoading}
        id="queryInput"
        placeholder={`Ask anything about ${guruTypePromptName}`}
        type="text"
        value={inputValue || ""}
        onBlur={handleMobileInputBlur}
        onChange={handleInputChange}
        onFocus={handleMobileInputFocus}
        onKeyPress={handleKeyPress}
      />
    </form>
  );
};

export default QueryInput;
