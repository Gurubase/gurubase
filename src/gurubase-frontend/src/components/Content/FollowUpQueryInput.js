"use client";
import ZoomIn from "@/assets/images/zoom-in-scale-up.svg";
import PostQuestion from "@/assets/images/post-question.svg";
import clsx from "clsx";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import FollowUpSearchComponent from "./FollowUpSearchComponent";

import { useAppDispatch, useAppSelector } from "@/redux/hooks";
import {
  setInvalidAnswer,
  setMobileInputFocused,
  setInputQuery,
  setInputValue
} from "@/redux/slices/mainFormSlice";

const FollowUpQueryInput = ({
  onSubmit,
  setTypesenseLoading,
  guruType,
  setContentWrapperWidth,
  setContentWrapperLeft,
  guruTypePromptName,
  onInputChange,
  enableTypeSense,
  atBottom = false,
  error,
  setError,
  inputId,
  sessionUserExists
}) => {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const postContentExist =
    useAppSelector((state) => state.mainForm.postContentExist) ?? false;

  // Add a state to track if the search bar is fixed
  const [isSearchBarFixed, setIsSearchBarFixed] = useState(false);

  const panelHintsListed = useAppSelector(
    (state) => state.mainForm.panelHintsListed
  );

  const mobileInputFocused = useAppSelector(
    (state) => state.mainForm.mobileInputFocused
  );
  const isClearButtonTouched = useRef(false);
  const nextFunction = useRef(null);

  const inputValue = useAppSelector((state) => state.mainForm.inputValue);

  // Add this selector
  const inputQuery = useAppSelector((state) => state.mainForm.inputQuery);

  // Add this effect to update local input when Redux state changes
  useEffect(() => {
    const input = getInput(inputId);
    if (input && inputQuery !== null) {
      input.value = inputQuery;
      // if (document.activeElement !== input) {
      // input.focus();
      //   const len = input.value.length;
      //   input.setSelectionRange(len, len);
      // }
    }
  }, [inputQuery, inputId]);

  // Add the error check function
  const checkErrorExist = (value) => {
    if (value.length < 10) {
      setError("* At least 10 characters required!");
      return true;
    }
    setError(null);
    return false;
  };

  useEffect(() => {
    const input = getInput(inputId);
    if (input) {
      input.value = "";
      dispatch(setInputQuery(null));
    }
  }, [dispatch, inputId]);

  useEffect(() => {
    const updateInputValue = () => {
      const input = getInput(inputId);
      if (input) {
        setInputValue(input.value);
      }
    };

    // Initial value set
    updateInputValue();

    // Set up mutation observer to watch for input changes
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (
          mutation.type === "attributes" ||
          mutation.type === "characterData"
        ) {
          updateInputValue();
        }
      });
    });

    const input = getInput(inputId);
    if (input) {
      // Watch for both value and attribute changes
      observer.observe(input, {
        attributes: true,
        characterData: true,
        childList: true,
        subtree: true
      });

      // Add input listener
      const handleInput = (e) => setInputValue(e.target.value);
      input.addEventListener("input", handleInput);

      // Add clear listener
      const clearButton = document.querySelector(".aa-ClearButton");
      clearButton?.addEventListener("click", () => setInputValue(""));

      return () => {
        observer.disconnect();
        input.removeEventListener("input", handleInput);
        clearButton?.removeEventListener("click", () => setInputValue(""));
      };
    }
  }, []); // Empty dependency array as we want this to run once on mount

  // if scroll y is greater than 100px then fixed the search bar to top of the page else not fixed to top of the page write a function to handle this and assign it to the scroll event listener and return the cleanup function to remove the event listener and return tailwind css classes to the form element to fixed to top of the page or not fixed to top of the page
  const handleScroll = () => {
    // Don't apply fixed positioning if content exists (search bar is already at bottom)
    if (postContentExist) return;

    if (typeof window !== "undefined") {
      const contentWrapper = document?.querySelector(".content-wrapper");
      setContentWrapperWidth(contentWrapper?.clientWidth + "px");
      setContentWrapperLeft(
        contentWrapper?.getBoundingClientRect().left + "px"
      );
    }

    const searchElement = document.querySelector(".fixed-search");
    const fixedClass = `fixed bottom-0 right-0 z-10 container flex-1 guru-sm:h-[6rem] guru-sm:flex guru-sm:justify-center guru-sm:items-end guru-sm:pb-4 guru-sm:px-2`;

    if (window.scrollY >= 30 && window.innerWidth <= 915) {
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

  // handle enter keyboard event to submit the form
  useEffect(() => {
    const handleKeyPress = (e) => {
      isClearButtonTouched.current = false;
      setTimeout(() => {
        if (e.key === "Enter") {
          e.preventDefault();

          // Add error check before submission
          const input = getInput(inputId);
          if (input && checkErrorExist(input.value)) {
            return;
          }

          setError(null);

          onSubmit(e, true);
        }
      }, 1000);
    };

    const handleMobileInputFocus = () => {
      if (window.innerWidth <= 915) {
        dispatch(setInvalidAnswer(null));
        dispatch(setMobileInputFocused(true));
        // prevent scroll when mobile input is focused
        document.body.style.overflow = "hidden";
        return;
      }
      dispatch(setMobileInputFocused(false));
    };

    const handleMobileInputBlur = (e) => {
      // if e.relatedTarget does not contains aa-ClearButton then set mobile input focused to false
      e.preventDefault();
      const isClearClicked =
        e.relatedTarget && e.relatedTarget.classList.contains("aa-ClearButton");

      if (isClearClicked || isClearButtonTouched.current) {
        if (window.innerWidth <= 915) {
          document.querySelector(".aa-Input")?.focus();
          dispatch(setMobileInputFocused(true));
        }
        return;
      }
      dispatch(setMobileInputFocused(false));
      document.body.style.overflow = "auto";
    };

    document
      .querySelector("#autocomplete")
      ?.addEventListener("keypress", handleKeyPress);

    document
      .querySelector("#autocomplete")
      ?.addEventListener(
        "keydown",
        () => (isClearButtonTouched.current = false)
      );

    // on focus set mobile input focused to true
    document.querySelector(".aa-Input")?.addEventListener("focus", () =>
      setTimeout(() => {
        clearTimeout(nextFunction.current);
        nextFunction.current = setTimeout(() => {
          handleMobileInputFocus();
        }, 10);
      }, 10)
    );
    document.querySelector(".aa-Input")?.addEventListener("blur", (e) =>
      setTimeout(() => {
        clearTimeout(nextFunction.current);
        nextFunction.current = setTimeout(() => {
          handleMobileInputBlur(e);
        }, 10);
      }, 10)
    );

    // handle clear button click with mousedown
    document
      .querySelector(".aa-ClearButton")
      ?.addEventListener("mousedown", (event) => {
        event.preventDefault(); // Prevent default behavior
        event.stopPropagation(); // Stop event propagation
        document.querySelector(".aa-Input")?.focus(); // Keep the input focused

        isClearButtonTouched.current = true;
      });

    // handle clear button with touchstart
    document
      .querySelector(".aa-ClearButton")
      ?.addEventListener("touchstart", (event) => {
        event.stopPropagation(); // Stop event propagation
        document.querySelector(".aa-Input")?.focus(); // Keep the input focused

        isClearButtonTouched.current = true;
      });

    // handle blur event with mobile-backdrop mousedown
    document
      .querySelector(".mobile-backdrop")
      ?.addEventListener("mousedown", (event) => {
        if (isClearButtonTouched.current) {
          dispatch(setMobileInputFocused(false));
          document.body.style.overflow = "auto";
        }
        isClearButtonTouched.current = false;
      });
    // handle blur event with mobile-backdrop touchstart
    document
      .querySelector(".mobile-backdrop")
      ?.addEventListener("touchstart", (event) => {
        if (isClearButtonTouched.current) {
          dispatch(setMobileInputFocused(false));
          document.body.style.overflow = "auto";
        }
        isClearButtonTouched.current = false;
      });

    return () => {
      document
        .querySelector("#autocomplete")
        ?.removeEventListener("keypress", handleKeyPress);

      document
        .querySelector("#autocomplete")
        ?.removeEventListener(
          "keydown",
          () => (isClearButtonTouched.current = false)
        );

      // on focus set mobile input focused to true
      document.querySelector(".aa-Input")?.removeEventListener("focus", () =>
        setTimeout(() => {
          handleMobileInputFocus();
        }, 100)
      );
      document.querySelector(".aa-Input")?.removeEventListener("blur", (e) =>
        setTimeout(() => {
          handleMobileInputBlur(e);
        }, 100)
      );

      // handle clear button click with mousedown
      document
        .querySelector(".aa-ClearButton")
        ?.removeEventListener("mousedown", (event) => {
          event.preventDefault(); // Prevent default behavior
          event.stopPropagation(); // Stop event propagation
          document.querySelector(".aa-Input")?.focus(); // Keep the input focused

          isClearButtonTouched.current = true;
        });

      // handle clear button with touchstart
      document
        .querySelector(".aa-ClearButton")
        ?.removeEventListener("touchstart", (event) => {
          event.stopPropagation(); // Stop event propagation
          document.querySelector(".aa-Input")?.focus(); // Keep the input focused

          isClearButtonTouched.current = true;
        });

      // handle blur event with mobile-backdrop mousedown
      document
        .querySelector(".mobile-backdrop")
        ?.removeEventListener("mousedown", (event) => {
          if (isClearButtonTouched.current) {
            dispatch(setMobileInputFocused(false));
            document.body.style.overflow = "auto";
          }
          isClearButtonTouched.current = false;
        });
      // handle blur event with mobile-backdrop touchstart
      document
        .querySelector(".mobile-backdrop")
        ?.removeEventListener("touchstart", (event) => {
          if (isClearButtonTouched.current) {
            dispatch(setMobileInputFocused(false));
            document.body.style.overflow = "auto";
          }
          isClearButtonTouched.current = false;
        });
    };
  }, [onSubmit, dispatch, inputId]);

  const handleSearchValueChange = (value) => {
    dispatch(setInputValue(value));
  };

  const getInput = (id) => {
    return document.querySelector(`[data-follow-up-input="${id}"]`);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (await sessionUserExists()) {
      // console.log("submitting question");
      e.preventDefault();
      const input = getInput(inputId);
      if (input && checkErrorExist(input.value)) {
        return;
      }
      setError(null);
      onSubmit(e, true);
    }
  };

  return (
    <div className="relative w-full">
      <form
        className={clsx(
          "bg-white border border-solid border-gray-100 flex w-full items-center h-12 px-4 pr-3 gap-3 rounded-full"
        )}
        onSubmit={(e) => handleSubmit(e)}>
        <button
          aria-label="icon with zoom in"
          type="submit"
          className="shrink-0 flex items-center justify-center w-6 h-6">
          <Image
            loading="lazy"
            src={ZoomIn}
            alt="Icon"
            className="w-5 h-5"
            width={20}
            height={20}
          />
        </button>
        <FollowUpSearchComponent
          inputId={inputId}
          onValueChange={handleSearchValueChange}
          sticky={atBottom}
          className="text-base"
          sessionUserExists={sessionUserExists}
        />
        {!enableTypeSense && (
          <button
            aria-label="icon with post question"
            type="submit"
            className="shrink-0 flex items-center justify-center w-8 h-8">
            <div
              className={clsx(
                "w-8 h-8 p-1.5 flex items-center justify-center transition-colors duration-200 rounded-full",
                inputValue?.length >= 10 ? "bg-[#1B242E]" : "bg-[#BABFC9]"
              )}>
              <Image
                src={PostQuestion}
                alt="Icon"
                className={clsx(
                  "w-3 h-3",
                  inputValue?.length >= 10 ? "brightness-0 invert" : ""
                )}
                width={10}
                height={10}
              />
            </div>
          </button>
        )}
      </form>
      {error && (
        <div className="absolute bottom-[-24px] left-4 text-red-500 text-xs font-medium">
          {error}
        </div>
      )}
    </div>
  );
};

export default FollowUpQueryInput;
