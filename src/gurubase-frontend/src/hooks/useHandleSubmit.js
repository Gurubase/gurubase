import { setCookie } from "cookies-next";

import { getAnswerFromMyBackend, getDataForSlugDetails } from "@/app/actions";
import { setAnswerErrorWithTimeout } from "@/lib/utils";
import { useAppDispatch, useAppSelector } from "@/redux/hooks";
import {
  setAskingQuestion,
  setContextError,
  setCurrentQuestionSlug,
  setHasFetched,
  setInputQuery,
  setInputValue,
  setInvalidAnswer,
  setIsAnswerValid,
  setIsLoading,
  setParentQuestionSlug,
  setQuestionSummary,
  setQuestionText,
  setResetMainForm,
  setSlugPageRendered,
  setStreamError,
  setValidAnswer
} from "@/redux/slices/mainFormSlice";
import { useAppNavigation } from "@/lib/navigation";

export const useHandleSubmit = (
  guruType,
  checkErrorExist,
  setError,
  triggerStreamUpdate = null,
  setContent = null,
  setQuestion = null,
  setDescription = null
) => {
  const dispatch = useAppDispatch();
  const navigation = useAppNavigation();
  const inputValue = useAppSelector((state) => state.mainForm.inputValue);
  const isSelfHosted = process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted";
  const currentQuestionSlug = useAppSelector(
    (state) => state.mainForm.currentQuestionSlug
  );
  const parentQuestionSlug = useAppSelector(
    (state) => state.mainForm.parentQuestionSlug
  );

  const handleSubmit = async (
    e,
    signal,
    isFollowUp = false,
    questionText = null,
    bingeId = null,
    newBinge = false,
    rootSlug = null
  ) => {
    if (e) {
      e?.preventDefault();
    }

    //console.log(
    //   "entered handle submit with args",
    //   isFollowUp,
    //   questionText,
    //   bingeId,
    //   newBinge,
    //   rootSlug
    // );

    window.scrollTo({
      top: 0
    });

    //console.log("setting valid answer to true");
    dispatch(setValidAnswer(true));
    dispatch(setInvalidAnswer(null));
    dispatch(setStreamError(false));
    dispatch(setContextError(false));

    dispatch(setInputQuery(inputValue));
    //console.log("set input query", inputValue);

    const isErrorExist = checkErrorExist(inputValue);

    //console.log("is error exist", isErrorExist);
    if (isErrorExist) {
      return;
    }

    dispatch(setAskingQuestion(true));
    dispatch(setIsLoading(true));
    //console.log("set is loading to true");

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
        times,
        parent_topics: parentTopics
      } = await getAnswerFromMyBackend(inputValue, guruType, bingeId);

      if (signal && signal.aborted) {
        dispatch(setResetMainForm());

        return;
      }

      //console.log("received summary");
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
      } else if (error && status === 490 && isSelfHosted) {
        setError(
          <span>
            Invalid OpenAI API Key.{" "}
            <a
              href="/settings"
              className="text-blue-500 hover:text-blue-700 underline"
              onClick={(e) => {
                e.preventDefault();
                navigation.push("/settings");
              }}>
              Configure a valid API key
            </a>{" "}
            to use the Guru.
          </span>
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
        //console.log("slug is not present");
        dispatch(setIsLoading(false));
        dispatch(setAskingQuestion(false));

        return;
      }

      // if (isFollowUp) {
      //   //console.log("handle submit binge id is", bingeId);
      //   //console.log("handle submit input value is", inputValue);
      //   const response = await getDataForSlugDetails(
      //     slug,
      //     guruType,
      //     bingeId,
      //     inputValue
      //   );
      //   const data = JSON.parse(response);
      //   //console.log("got the slug details");
      //   console.log("Will check for slug:", slug);
      //   if (data.content && data.question) {
      //     console.log("question exists, updating content");
      //     // dispatch(setInputQuery(""));
      //     // dispatch(setInputValue(""));
      //     // dispatch(setIsLoading(false));

      //     // Question exists, update content using handleQuestionUpdate
      //     //console.log("calling handleQuestionUpdate with slug", slug);
      //     //console.log(
      //     //   "calling handleQuestionUpdate with input value",
      //     //   inputValue
      //     // );
      //     await handleQuestionUpdate({
      //       guruType,
      //       newSlug: slug,
      //       oldSlug: currentQuestionSlug,
      //       dispatch,
      //       setContent,
      //       setQuestion,
      //       setDescription,
      //       bingeId,
      //       inputValue,
      //       content: data.content,
      //       question: data.question,
      //       description: data.description,
      //       references: data.references,
      //       trustScore: data.trust_score,
      //       dateUpdated: data.date_updated,
      //       followUpQuestions: data.follow_up_questions
      //     });
      //     //console.log("content updated");
      //     return;
      //   }
      // }

      //console.log("setting valid answer to", answerValid);
      dispatch(setValidAnswer(answerValid));
      dispatch(setInvalidAnswer(description));

      // console.log("answerValid", answerValid);

      if (!answerValid) {
        await setAnswerErrorWithTimeout(dispatch, "answerIsInvalid");
        dispatch(setIsLoading(false));
        dispatch(setAskingQuestion(false));
        dispatch(setIsAnswerValid(answerValid));

        return;
      }

      if (signal.aborted) {
        dispatch(setResetMainForm());
        dispatch(setAskingQuestion(false));

        return;
      }

      const summaryData = {
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
        times,
        parent_topics: parentTopics
      };

      dispatch(setQuestionSummary(summaryData));
      //console.log("set question summary");

      setCookie("questionSummary", {
        ...summaryData,
        answerValid
      });
      //console.log("set summary cookie");

      dispatch(setSlugPageRendered(false));

      if (signal.aborted) {
        dispatch(setResetMainForm());

        return;
      }

      dispatch(setCurrentQuestionSlug(slug));

      dispatch(setHasFetched(false));
      if (!isFollowUp) {
        navigation.push(`/g/${guruType}/${slug}?question=${question}`);
        //console.log("redirect to slug page");
      } else {
        //console.log("need to trigger stream update");
        if (triggerStreamUpdate) {
          //console.log("triggering stream update");
          await triggerStreamUpdate(summaryData);
        }
      }
    } catch (error) {
      if (error.status === 405) {
        dispatch(setStreamError({ status: 405, message: error.message }));
      } else {
        dispatch(setStreamError({ status: 500, message: null }));
      }
    }
  };

  return handleSubmit;
};
