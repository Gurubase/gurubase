import clsx from "clsx";
import { setCookie } from "cookies-next";
import { ArrowLeft } from "lucide-react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import React, { useCallback, useEffect, useState } from "react";

import { getAnswerFromMyBackend, getDataForSlugDetails } from "@/app/actions";
import DefaultQuerySection from "@/components/Content/DefaultQuerySection";
import QueryInput from "@/components/Content/QueryInput";
import { getGuruPromptMap } from "@/components/Header/utils";
import { useSubmitWithAbort } from "@/hooks/useSubmitWithAbort";
import { setAnswerErrorWithTimeout } from "@/lib/utils";
import { useAppDispatch, useAppSelector } from "@/redux/hooks";
import {
  resetErrors,
  setAskingQuestion,
  setContextError,
  setCurrentQuestionSlug,
  setHasFetched,
  setInputQuery,
  setInputValue,
  setInvalidAnswer,
  setIsAnswerValid,
  setIsLoading,
  setMobileInputFocused,
  setPostContentExist,
  setQuestionSummary,
  setResetMainForm,
  setSlugPageRendered,
  setStreamError,
  setStreamingStatus
} from "@/redux/slices/mainFormSlice";
import { handleQuestionUpdate } from "@/utils/handleQuestionUpdate";
import useIsSmallScreen from "@/utils/hooks/useIsSmallScreen";
import usePreventScroll from "@/utils/hooks/usePreventScroll";

import InfoWarningErrorBanner from "../InfoWarningErrorBanner";

// Extract handleSubmit as a standalone function
export const handleSubmitQuestion = async ({
  e,
  signal,
  inputValue,
  guruType,
  dispatch,
  router,
  setError,
  checkErrorExist,
  redirect
}) => {
  if (e) {
    e?.preventDefault();
  }
  // Unfocus input on submit
  if (document.activeElement instanceof HTMLElement) {
    document.activeElement.blur();
  }
  dispatch(setInputQuery(inputValue));
  dispatch(setInputValue(inputValue));
  dispatch(resetErrors());
  dispatch(setMobileInputFocused(false));

  const isErrorExist = checkErrorExist?.(inputValue);
  const isSelfHosted = process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted";

  if (isErrorExist) {
    return;
  }

  e?.preventDefault();

  dispatch(setAskingQuestion(true));
  dispatch(setIsLoading(true));
  try {
    const {
      question_slug: slug,
      question,
      description,
      completion_tokens,
      answer_length,
      user_intent,
      prompt_tokens,
      retry_count,
      error,
      status,
      valid_question: answerValid,
      jwt,
      times
    } = await getAnswerFromMyBackend(inputValue, guruType, null);

    if (signal?.aborted) {
      dispatch(setResetMainForm());

      return;
    }

    if (error && status === 429) {
      dispatch(setIsLoading(false));
      dispatch(setAskingQuestion(false));

      return;
    } else if (error && status === 425 && isSelfHosted) {
      setError(
        "The reranker model is downloading and not ready yet. Check the gurubase-reranker container health for details."
      );
      dispatch(setIsLoading(false));
      dispatch(setAskingQuestion(false));

      return;
    } else if (error) {
      setError("Error while asking question! Please try again.");
      dispatch(setIsLoading(false));
      dispatch(setAskingQuestion(false));

      return;
    }

    if (!slug) {
      // if slug is not present then return from function
      dispatch(setIsLoading(false));
      dispatch(setAskingQuestion(false));

      return;
    }
    if (!answerValid) {
      await setAnswerErrorWithTimeout(dispatch, "answerIsInvalid");
    }
    dispatch(setIsAnswerValid(answerValid));
    dispatch(setInvalidAnswer(description));
    if (!answerValid && slug) {
      // if answer is not valid then return from function but redirect to content page with the slug and do not save to sitemap
      dispatch(setIsLoading(false));
      dispatch(setAskingQuestion(false));

      return;
    }
    // redirect to slug page
    // if everything is fine then save it to redux store to get in the post content page
    if (signal?.aborted) {
      dispatch(setResetMainForm());
      dispatch(setAskingQuestion(false));

      return;
    }

    dispatch(
      setQuestionSummary({
        question,
        description,
        completion_tokens,
        answer_length,
        user_intent,
        prompt_tokens,
        jwt,
        user_question: inputValue,
        times
      })
    );

    setCookie("questionSummary", {
      question,
      question_slug: slug,
      description,
      completion_tokens,
      answer_length,
      user_intent,
      prompt_tokens,
      retry_count,
      jwt,
      user_question: inputValue,
      answerValid,
      times
    });

    dispatch(setSlugPageRendered(false));
    dispatch(setHasFetched(false));
    dispatch(setCurrentQuestionSlug(slug));
    if (signal?.aborted) {
      dispatch(setResetMainForm());

      return;
    }
    if (redirect) {
      router.push(`/g/${guruType}/${slug}?question=${question}`);
    }
  } catch (error) {
    // console.error("error in main form catch ", error);
  }
};

const MainForm = ({
  question,
  content,
  guruType,
  allGuruTypes,
  defaultQuestions,
  input,
  setInput,
  triggerStreamUpdate,
  setContent,
  setQuestion,
  setDescription
}) => {
  const router = useRouter();
  const [error, setError] = useState(null);
  const isAnswerValid = useAppSelector((state) => state.mainForm.isAnswerValid);
  const [contentWrapperWidth, setContentWrapperWidth] = useState("1180px");
  const [contentWrapperLeft, setContentWrapperLeft] = useState("0px");

  const streamError = useAppSelector((state) => state.mainForm.streamError);
  const contextError = useAppSelector((state) => state.mainForm.contextError);
  const streamingStatus = useAppSelector(
    (state) => state.mainForm.streamingStatus
  );

  const panelHintsListed = useAppSelector(
    (state) => state.mainForm.panelHintsListed
  );

  const mobileInputFocused = useAppSelector(
    (state) => state.mainForm.mobileInputFocused
  );

  // Use the hook to prevent scrolling when the mobileInputFocused is true
  usePreventScroll(mobileInputFocused);

  const isLoading = useAppSelector((state) => state.mainForm.isLoading);
  const isSmallScreen = useIsSmallScreen();
  const postContentExist = useAppSelector(
    (state) => state.mainForm.postContentExist
  );
  const inputValue = useAppSelector((state) => state.mainForm.inputValue);
  const searchParams = useSearchParams();
  const { slug: root_slug, bingeId: url_binge_id } = useParams();
  const dispatch = useAppDispatch();

  const handleButtonClick = useCallback(
    (query) => {
      dispatch(setInputValue(query.question));
      dispatch(setInputQuery(query.question));
      // router.push(`/guru/${guruType}/${query?.slug}`);
    },
    [dispatch, router, guruType]
  );

  const checkErrorExist = (inputValue) => {
    if (inputValue.length < 10) {
      setError("* At least 10 characters required!");

      return true;
    }
    setError(null);

    return false;
  };

  const bingeId = useAppSelector((state) => state.mainForm.bingeId);

  useEffect(() => {
    if (!input || streamingStatus || content) {
      return;
    }
    const controller = new AbortController();

    if (!streamingStatus) {
      handleSubmit(input, controller.signal);
    }

    return () => {
      controller.abort();
    };
  }, [input, streamingStatus]);

  const handleSubmit = async (e, signal) => {
    await handleSubmitQuestion({
      e,
      signal,
      inputValue,
      guruType,
      dispatch,
      router,
      setError,
      checkErrorExist,
      redirect: true
    });
  };

  useEffect(() => {
    if (mobileInputFocused) {
      dispatch(setMobileInputFocused(false));
      if (typeof window !== "undefined" && typeof document !== "undefined") {
        document.body.style.overflow = "auto";
      }
    }
  }, []);

  useEffect(() => {
    if (
      !isLoading &&
      question &&
      content &&
      isAnswerValid &&
      setPostContentExist
    ) {
      dispatch(setPostContentExist(true));
    } else {
      dispatch(setPostContentExist(false));
    }
  }, [isLoading, isAnswerValid, question, content, dispatch]);

  const disableScroll = () => {
    if (typeof window === "undefined") return;
  };

  const enableScroll = () => {
    if (typeof window === "undefined") return;
  };

  useEffect(() => {
    if (!mobileInputFocused) {
      disableScroll();
      const aaPanel = document.querySelector(".aa-Panel");

      if (aaPanel) {
        aaPanel.remove();
      }
    } else {
      enableScroll();
    }
  }, [mobileInputFocused]);

  const isBingeMapOpen = useAppSelector(
    (state) => state.mainForm.isBingeMapOpen
  );

  const goBack = async () => {
    let question_slug = searchParams.get("question_slug");

    if (!question_slug) {
      question_slug = root_slug;
    }

    dispatch(resetErrors());

    let bingeIdToUse = url_binge_id || bingeId;

    if (root_slug && bingeIdToUse && question_slug) {
      dispatch(setStreamError(false));
      dispatch(setContextError(false));
      dispatch(setStreamingStatus(false));
      dispatch(setQuestionSummary(null));
      dispatch(setIsLoading(false));
      try {
        const response = await getDataForSlugDetails(
          question_slug,
          guruType,
          bingeIdToUse,
          ""
        );
        const data = JSON.parse(response);

        if (data.content && data.question) {
          await handleQuestionUpdate({
            guruType,
            newSlug: question_slug,
            oldSlug: question_slug,
            dispatch,
            setContent,
            setQuestion,
            setDescription,
            bingeIdToUse,
            content: data.content,
            question: data.question,
            description: data.description,
            references: data.references,
            trustScore: data.trust_score,
            dateUpdated: data.date_updated,
            followUpQuestions: data.follow_up_questions
          });
        }
      } catch (error) {
        // console.error("Error loading question from URL:", error);
      }
    }
  };

  const submitWithAbortController = useSubmitWithAbort(
    guruType,
    setInput,
    checkErrorExist,
    setError,
    triggerStreamUpdate,
    setContent,
    setQuestion,
    setDescription
  );

  const SlugPageRendered = useAppSelector(
    (state) => state.mainForm.slugPageRendered
  );

  return (
    <section
      className={clsx(
        "flex flex-col w-full guru-sm:max-w-full",
        mobileInputFocused ? "pb-0" : "pb-4"
      )}>
      {(!content || isLoading || (!SlugPageRendered && streamingStatus)) &&
        (!bingeId || (!streamError && !contextError && isAnswerValid)) && (
          <div
            className={clsx(
              "flex flex-col guru-sm:px-4 px-5 guru-sm:max-w-full  guru-sm:border-solid guru-sm:border-b guru-sm:border-b-neutral-200 mt-10 guru-sm:mt-0 guru-sm:pb-4 ",
              guruType || postContentExist || isLoading
                ? "guru-sm:border-b"
                : "guru-sm:border-none",
              guruType || postContentExist || isLoading
                ? mobileInputFocused
                  ? "guru-sm:mb-0"
                  : "guru-sm:mb-2"
                : " guru-sm:mb-1",
              mobileInputFocused ? "justify-start" : "justify-center",
              mobileInputFocused
                ? "fixed inset-0  bg-black-base bg-opacity-50 backdrop-blur-md  z-10 guru-sm:px-4 mobile-backdrop"
                : guruType || postContentExist || isLoading
                  ? "" // Go to inline style in the bottom
                  : "guru-sm:bg-white bg-white",
              isBingeMapOpen ? "guru-lg:block hidden" : ""
            )}>
            <div
              className={clsx(
                "fixed-search guru-md:rounded-b-none rounded-b-[20px] transition-transform duration-300",
                mobileInputFocused
                  ? " "
                  : guruType || postContentExist || isLoading
                    ? `bg-white ` // go to next line for dynamic bg color for sm
                    : " bg-white"
              )}
              style={{
                maxWidth: contentWrapperWidth,
                left: contentWrapperLeft,
                backgroundColor: ""
              }}>
              <div
                className={clsx(
                  "flex flex-col justify-center  h-fit text-base border border-solid border-gray-85  text-gray-400 guru-sm:max-w-full guru-sm:flex-grow  mobile-fixed-search",
                  "relative",
                  mobileInputFocused ? "mt-[82px] border-none" : "",
                  panelHintsListed ? "rounded-t-[30px]" : "rounded-[40px]"
                )}>
                <div className="flex flex-col justify-center guru-sm:max-w-full">
                  <QueryInput
                    guruType={guruType}
                    guruTypePromptName={getGuruPromptMap(
                      guruType,
                      allGuruTypes
                    )}
                    setContentWrapperLeft={setContentWrapperLeft}
                    setContentWrapperWidth={setContentWrapperWidth}
                    onSubmit={submitWithAbortController}
                  />
                </div>
              </div>
              <div className="error not-prose text-[0.8rem]">
                {error && (
                  <p className="text-red-500 ml-8 not-prose">{error}</p>
                )}
              </div>
            </div>
          </div>
        )}
      {!question && !content && !isLoading && defaultQuestions?.length > 0 ? (
        <div className="flex flex-col justify-center guru-sm:px-4 px-5">
          <DefaultQuerySection
            defaultQuestions={defaultQuestions}
            guruType={guruType}
            handleButtonClick={handleButtonClick}
          />
        </div>
      ) : null}
      {!isLoading && streamError && (
        <InfoWarningErrorBanner type="warning">
          <p className="text-zinc-900">
            {streamError.status === 405
              ? streamError.message
              : "There was an error in the stream. We are investigating the issue. Please try again later."}
          </p>
        </InfoWarningErrorBanner>
      )}
      {!isLoading && contextError && (
        <InfoWarningErrorBanner type="warning">
          <p className="text-zinc-900">
            {getGuruPromptMap(guruType, allGuruTypes)} Guru doesn&apos;t have
            enough data as a source to generate a reliable answer for this
            question.
          </p>
        </InfoWarningErrorBanner>
      )}
      {!isLoading && !isAnswerValid && (
        <InfoWarningErrorBanner type="warning">
          <p className="text-zinc-900">
            This question is not related to{" "}
            {getGuruPromptMap(guruType, allGuruTypes)}.
          </p>
        </InfoWarningErrorBanner>
      )}
      {bingeId &&
        !isLoading &&
        (streamError || contextError || !isAnswerValid) && (
          <div className="flex justify-center mt-4">
            <button
              className="bg-[#1B242D] text-white hover:bg-[#2A3744] hover:text-white rounded-full h-auto px-6 py-3 text-sm font-medium transition-colors duration-200 max-w-[500px] flex items-center"
              onClick={goBack}>
              <ArrowLeft className="mr-2 h-5 w-5" />
              Back to last question
            </button>
          </div>
        )}
    </section>
  );
};

export default MainForm;
