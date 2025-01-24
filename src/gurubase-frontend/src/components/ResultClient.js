"use client";

import mixpanel from "mixpanel-browser";
import { notFound, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { getDataForSlugDetails, getExampleQuestions } from "@/app/actions";
import Content from "@/components/Content";
import { handleSubmitQuestion } from "@/components/Content/MainForm";
import Footer from "@/components/Footer";
import Header from "@/components/Header";
import LoginModal from "@/components/LoginModal/index";
import { setAnswerErrorWithTimeout } from "@/lib/utils";
import { useAppDispatch, useAppSelector } from "@/redux/hooks";
import {
  setAskingQuestion,
  setBingeId,
  setContextError,
  setCurrentQuestionSlug,
  setFollowUpQuestions,
  setHasFetched,
  setInputQuery,
  setIsLoading,
  setNotFoundContext,
  setParentQuestionSlug,
  setQuestionSummary,
  setSlugPageRendered,
  setStreamError,
  setStreamingStatus,
  setWaitingForFirstChunk
} from "@/redux/slices/mainFormSlice";
import { bingeRedirection } from "@/utils/bingeRedirection";
import { getStream } from "@/utils/clientActions";

export const ResultClient = ({
  isHelpful,
  slug,
  guruType,
  passedBingeId = null,
  instantContent,
  instantDescription,
  instantQuestion,
  references,
  similarQuestions,
  allGuruTypes,
  dirty,
  dateUpdated,
  trustScore
}) => {
  const dispatch = useAppDispatch();
  const router = useRouter();
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);

  // Move all hooks to the top, before any conditional logic
  useEffect(() => {
    // Initialize current slug with prop
    dispatch(setCurrentQuestionSlug(slug));
  }, [slug, dispatch]);

  const [data, setData] = useState(instantContent || "");
  const [currentSlug, setCurrentSlug] = useState(slug);
  const [isInitializing, setIsInitializing] = useState(dirty);

  const [fingerprint, setFingerprint] = useState(null);
  const isLoading = useAppSelector((state) => state.mainForm.isLoading);
  const hasFetched = useAppSelector((state) => state.mainForm.hasFetched);

  // questionSummary from the redux store
  const questionSummary = useAppSelector(
    (state) => state.mainForm.questionSummary
  );

  const bingeId = useAppSelector((state) => state.mainForm.bingeId);

  const parentQuestionSlug = useAppSelector(
    (state) => state.mainForm.parentQuestionSlug
  );

  const currentQuestionSlug = useAppSelector(
    (state) => state.mainForm.currentQuestionSlug
  );

  const slugPageRendered = useAppSelector(
    (state) => state.mainForm.slugPageRendered
  );

  const hasInitialized = useRef(false);

  const {
    question: reduxQuestion = "",
    description: reduxDescription = "",
    prompt_tokens = 0,
    completion_tokens = 0,
    user_intent = "",
    answer_length = "",
    jwt,
    user_question,
    times
  } = questionSummary || {};

  // Add this effect to handle initial dirty state
  useEffect(() => {
    const initializeDirtyQuestion = async (instantQuestion) => {
      if (dirty && !instantContent && !hasInitialized.current) {
        hasInitialized.current = true;

        await handleSubmitQuestion({
          inputValue: instantQuestion,
          guruType,
          dispatch,
          router,
          setError: () => {},
          checkErrorExist: () => false,
          redirect: false
        });
        setIsInitializing(false);
      }
    };

    if (dirty && !hasInitialized.current) {
      initializeDirtyQuestion(instantQuestion);
    }
  }, [dirty, instantContent, guruType, dispatch, router]);

  // Add this new useEffect for loading Algolia autocomplete theme
  // useEffect(() => {
  //   const loadAlgoliaTheme = async () => {
  //     const link = document.createElement("link");

  //     link.href =
  //       "https://cdn.jsdelivr.net/npm/@algolia/autocomplete-theme-classic";
  //     link.rel = "stylesheet";
  //     document.head.appendChild(link);
  //   };

  //   loadAlgoliaTheme();
  // }, []);

  // useEffect(() => {
  //   if (!fingerprint || !slug || typeof window === "undefined") return;
  //   recordVisit(guruType, slug, fingerprint);
  //   // .catch((error) =>
  //   //   console.error("Error recording visit:", error)
  //   // );
  // }, [fingerprint]);

  useEffect(() => {
    if (!slug || typeof window === "undefined" || fingerprint) {
      return;
    }
    if (process.env.NEXT_PUBLIC_MIXPANEL_TOKEN) {
      mixpanel.init(process.env.NEXT_PUBLIC_MIXPANEL_TOKEN, { debug: false });
      mixpanel.track("Slug Visited", {
        slug: slug,
        guruType: guruType
      });
    }
  }, []);

  const [question, setQuestion] = useState(instantQuestion || reduxQuestion);
  const [description, setDescription] = useState(
    instantDescription || reduxDescription
  );

  // when users visit this page first time set dispatch slugPageRendered to true
  useEffect(() => {
    dispatch(setSlugPageRendered(true));
  }, [dispatch]);

  useEffect(() => {
    // when its completed remove question param from the url javascript/handling-closures-in-javascript?question=Handling%20closures%20in%20JavaScript
    // Remove the question parameter from the URL
    const url = new URL(window.location.href);

    if (url.searchParams.has("question")) {
      url.searchParams.delete("question");
      router.replace(url.pathname, undefined, {
        scroll: false,
        shallow: true
      });
    }
  }, [router]);

  // Set binge ID in Redux store if passed as prop on initial load
  useEffect(() => {
    if (passedBingeId) {
      dispatch(setBingeId(passedBingeId));
    }
  }, [passedBingeId, dispatch]);

  useEffect(() => {
    //console.log("entered stream effect");
    //console.log("early return", hasFetched, !!data);
    if (hasFetched || data) {
      dispatch(setIsLoading(false));

      return;
    }

    // fetch data for stream question
    const fetchStreamData = async () => {
      //console.log("entered fetch stream data");
      try {
        dispatch(setIsLoading(true));
        //console.log("set is loading to true");
        dispatch(setSlugPageRendered(false)); // when stream start do not show prev content in the page
        //console.log("set slug page rendered to false");
        dispatch(setStreamingStatus(true));
        //console.log("set streaming status to true");
        dispatch(setStreamError(false));
        //console.log("set stream error to false");
        dispatch(setContextError(false)); // Reset context error state
        dispatch(setWaitingForFirstChunk(true));

        //console.log("parent question slug", parentQuestionSlug);
        //console.log("current slug", currentQuestionSlug);

        const payload = {
          question: question,
          question_slug: currentQuestionSlug,
          description: description,
          retry_count: 1,
          completion_tokens: completion_tokens,
          answer_length: answer_length,
          user_intent: user_intent,
          prompt_tokens: prompt_tokens,
          user_question: user_question,
          parent_question_slug: parentQuestionSlug || null,
          binge_id: passedBingeId || bingeId || null,
          times: times
        };

        const response = await getStream(payload, guruType, jwt);

        //console.log("got the response from stream");

        if (!response.ok || !response.body) {
          dispatch(setIsLoading(false));
          dispatch(setWaitingForFirstChunk(false));

          if (response.status === 406) {
            await setAnswerErrorWithTimeout(dispatch, "context");
            dispatch(setContextError(true));
            //console.log("set context error to true");
          } else if (response.status === 405) {
            // Get error message from response
            const errorData = await response.json();

            //console.log("errorData", errorData);
            dispatch(setStreamError({ status: 405, message: errorData.msg }));
            //console.log("set stream error");
          } else {
            await setAnswerErrorWithTimeout(dispatch, "stream");
            dispatch(setStreamError(true));
            //console.log("set stream error to true");
          }
          dispatch(setIsLoading(false));
          dispatch(setSlugPageRendered(true));
          dispatch(setAskingQuestion(false));
          if (!bingeId) {
            router.push(`/g/${guruType}`);
          }
          throw new Error(response.statusText);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        dispatch(setInputQuery(""));
        //console.log("set input query to empty");
        while (true) {
          const { value, done } = await reader.read();

          if (done) {
            dispatch(setStreamingStatus(false));
            dispatch(setAskingQuestion(false));
            dispatch(setQuestionSummary(null));
            dispatch(setIsLoading(false));

            const response = await getDataForSlugDetails(
              currentQuestionSlug,
              guruType,
              passedBingeId || bingeId || null,
              ""
            );

            const data = JSON.parse(response);
            const trustScore = data.trust_score;

            const dateUpdated = data.date_updated;
            const references = data.references;
            const followUpQuestions = data.follow_up_questions;

            bingeRedirection({
              dispatch,
              newSlug: currentQuestionSlug,
              oldSlug: parentQuestionSlug,
              questionText: question,
              guruType,
              bingeId: passedBingeId || bingeId,
              trustScore,
              dateUpdated,
              references,
              followUpQuestions
            });

            const generatedFollowUpQuestions = await getExampleQuestions(
              guruType,
              passedBingeId || bingeId,
              currentQuestionSlug,
              question
            );

            dispatch(setFollowUpQuestions(generatedFollowUpQuestions));

            break;
          }

          const decodedChunk = decoder.decode(value, { stream: true });

          if (decodedChunk) {
            if (!slugPageRendered) {
              dispatch(setWaitingForFirstChunk(false));
              setTimeout(() => {
                dispatch(setIsLoading(false));
                dispatch(setSlugPageRendered(true)); // when stream has started with first chuck show the content
              }, 700);
            }
          }
          // add decodedChunk to data
          setData((prevData) => `${prevData}${decodedChunk}`);
        }
      } catch (error) {
        // Handle other errors
        dispatch(setWaitingForFirstChunk(false));
        dispatch(setIsLoading(false));
        dispatch(setAskingQuestion(false));
        dispatch(setStreamingStatus(false));
        dispatch(setSlugPageRendered(true));
      }
    };

    if (
      question &&
      description &&
      prompt_tokens &&
      completion_tokens &&
      answer_length &&
      user_intent &&
      slug &&
      !hasFetched
    ) {
      //console.log("need to fetch stream data");
      fetchStreamData();
      dispatch(setHasFetched(true));

      //console.log("set has fetched to true");
    } else {
      if (!isInitializing) {
        // Set not found context before calling notFound
        dispatch(
          setNotFoundContext({
            errorType: "404",
            component: "ResultClient",
            reason: `Will try to stream but it is not suitable.`,
            question,
            description,
            prompt_tokens,
            completion_tokens,
            answer_length,
            user_intent,
            slug,
            dirty,
            isInitializing,
            hasFetched
          })
        );
        notFound();
      }
    }
  }, [
    hasFetched,
    question,
    description,
    prompt_tokens,
    completion_tokens,
    answer_length,
    user_intent,
    currentQuestionSlug,
    instantContent,
    jwt,
    user_question,
    dispatch,
    isInitializing
  ]);

  // if window is undefined it mean it is server side rendering and instantContent is not available so redirect to not found page
  if (typeof window === "undefined" && !instantContent && !dirty) {
    // Set not found context for server-side case
    dispatch(
      setNotFoundContext({
        errorType: "404",
        component: "ResultClient",
        reason: `No content exists while js is disabled.`,
        dirty,
        instantContent,
        slug,
        question,
        description,
        prompt_tokens,
        completion_tokens,
        answer_length,
        user_intent,
        user_question
      })
    );
    notFound();
  }

  const triggerStreamUpdate = (summaryData) => {
    // Store the old slug as parent before updating current
    const oldSlug = currentQuestionSlug;

    // Update current slug first
    dispatch(setCurrentQuestionSlug(summaryData.question_slug));
    // return;
    setCurrentSlug(summaryData.question_slug);

    // Then set parent using the stored old slug
    dispatch(setParentQuestionSlug(oldSlug));
    //console.log("in trigger stream update set parent question slug", oldSlug);

    // Rest of the updates
    dispatch(setQuestionSummary(summaryData));
    setQuestion(summaryData.question);
    setDescription(summaryData.description);
    dispatch(setHasFetched(false));
    setData("");
  };

  // If Javascript is enabled, use the slug from the Redux store, otherwise use the slug from the URL
  const finalSlug = typeof window !== "undefined" ? currentQuestionSlug : slug;

  return (
    <main className="flex flex-col bg-white h-screen">
      <Header allGuruTypes={allGuruTypes} guruType={guruType} />
      <Content
        allGuruTypes={allGuruTypes}
        content={data}
        dateUpdated={dateUpdated}
        description={description}
        guruType={guruType}
        isHelpful={isHelpful}
        passedBingeId={passedBingeId}
        question={question}
        references={references || []}
        setContent={setData}
        setDescription={setDescription}
        setQuestion={setQuestion}
        setShowLoginModal={setIsLoginModalOpen}
        similarQuestions={similarQuestions}
        slug={finalSlug}
        triggerStreamUpdate={triggerStreamUpdate}
        trustScore={trustScore}
      />
      <Footer guruType={guruType} slug={finalSlug} />
      <LoginModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
      />
    </main>
  );
};