import { useUser } from "@auth0/nextjs-auth0/client";
import clsx from "clsx";
import { Clock, X } from "lucide-react";
import dynamic from "next/dynamic";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import BingeMapIcon from "@/assets/images/binge-map.svg";
import NewQuestionIcon from "@/assets/images/new-question.svg";
import AnswerLastModified from "@/components/AnswerLastModified";
import BingeMap from "@/components/BingeMap/index";
import FollowUpQueryInput from "@/components/Content/FollowUpQueryInput";
import CurrentlyAsking from "@/components/CurrentlyAsking";
import { getGuruPromptMap } from "@/components/Header/utils";
import PostContent from "@/components/PostContent";
import Sources from "@/components/sources/Sources";
import { Button } from "@/components/ui/button";
import { useBingeMap } from "@/hooks/useBingeMap";
import { useSubmitWithAbort } from "@/hooks/useSubmitWithAbort";
import { useAppDispatch, useAppSelector } from "@/redux/hooks";
import {
  setInputQuery,
  setInputValue,
  setIsBingeMapOpen,
  setResetMainForm,
  setFollowUpQuestions
} from "@/redux/slices/mainFormSlice";

import OtherGurus from "../OtherGurus";
import SimilarQuestions from "../SimilarQuestions";
import ExampleQuestions from "../FollowUpQuestions";
import { getExampleQuestions } from "@/app/actions";
import { useAppNavigation } from "@/lib/navigation";

const MainForm = dynamic(() => import("@/components/Content/MainForm"));

const Content = (props) => {
  const {
    question,
    content,
    isHelpful,
    slug,
    description,
    guruType,
    references,
    similarQuestions,
    allGuruTypes,
    resources,
    trustScore,
    dateUpdated,
    triggerStreamUpdate,
    setContent,
    setQuestion,
    setDescription,
    passedBingeId,
    setShowLoginModal,
    source
  } = props;

  const currentQuestionSlug = useAppSelector(
    (state) => state.mainForm.currentQuestionSlug
  );

  const [exampleQuestions, setExampleQuestions] = useState([]);

  const reduxFollowUpQuestions = useAppSelector(
    (state) => state.mainForm.followUpQuestions
  );

  useEffect(() => {
    setExampleQuestions(reduxFollowUpQuestions);
  }, [reduxFollowUpQuestions]);

  // Redux'tan bingeId'yi al
  const reduxBingeId = useAppSelector((state) => state.mainForm.bingeId);

  const questionText = useAppSelector((state) => state.mainForm.questionText);

  // JavaScript kapalıyken props'tan gelen bingeId'yi kullan
  const finalBingeId =
    typeof window !== "undefined"
      ? reduxBingeId || passedBingeId // JavaScript açıkken Redux veya props
      : passedBingeId; // JavaScript kapalıyken direkt props

  useEffect(() => {
    const fetchExampleQuestions = async () => {
      const followUpQuestions = await getExampleQuestions(
        guruType,
        finalBingeId,
        currentQuestionSlug,
        questionText
      );
      dispatch(setFollowUpQuestions(followUpQuestions));
    };
    fetchExampleQuestions();
  }, [currentQuestionSlug, finalBingeId, guruType, questionText]);

  const [typesenseLoading, setTypesenseLoading] = useState(false);
  const [contentWrapperWidth, setContentWrapperWidth] = useState("1180px");
  const [contentWrapperLeft, setContentWrapperLeft] = useState("0px");
  const isLoading = useAppSelector((state) => state.mainForm.isLoading);
  const dispatch = useAppDispatch();
  const inputValue = useAppSelector((state) => state.mainForm.inputValue);
  const streamError = useAppSelector((state) => state.mainForm.streamError);
  const contextError = useAppSelector((state) => state.mainForm.contextError);
  const [error, setError] = useState(null);
  const validAnswer = useAppSelector((state) => state.mainForm.validAnswer);

  const checkErrorExist = (value) => {
    if (value.length < 10) {
      //console.log("error", value);
      setError("* At least 10 characters required!");

      return true;
    }
    setError(null);

    return false;
  };

  // console.log("finalBingeId", finalBingeId);

  const navigation = useAppNavigation();

  const newQuestionClick = () => {
    if (guruType) {
      dispatch(setResetMainForm());
      navigation.setHref(`/g/${guruType}`);
    }
  };

  const [isScrolledToBottom, setIsScrolledToBottom] = useState(false);
  // Add debounce timeout ref
  const scrollTimeoutRef = useRef(null);
  // Add last state ref to implement hysteresis
  const lastScrollStateRef = useRef(false);

  // window genişliği için state
  const [windowWidth, setWindowWidth] = useState(
    typeof window !== "undefined" ? window.innerWidth : 0
  );

  // window genişliğini client-side'da takip et
  useEffect(() => {
    // İlk render'da window genişliğini al
    setWindowWidth(window.innerWidth);

    // Resize event listener ekle
    const handleResize = () => {
      setWindowWidth(window.innerWidth);
    };

    window.addEventListener("resize", handleResize);

    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // checkIfScrolledToBottom fonksiyonunu güncelle
  const checkIfScrolledToBottom = (buffer = 312) => {
    if (typeof window === "undefined") return;

    const bottomSearchContainer = document.querySelector(
      "#bottom-search-container"
    );
    const bottomSearchBarRect = bottomSearchContainer?.getBoundingClientRect();

    const isBottomSearchVisible =
      bottomSearchBarRect &&
      bottomSearchBarRect.top <=
        window.innerHeight - bottomSearchBarRect.height; // windowWidth yerine window.innerHeight kullanmalıyız

    if (isBottomSearchVisible) {
      setIsScrolledToBottom(true);
      lastScrollStateRef.current = true;

      return;
    }

    setIsScrolledToBottom(false);
    lastScrollStateRef.current = false;
  };

  const handleScroll = () => {
    // Clear existing timeout
    if (scrollTimeoutRef.current) {
      clearTimeout(scrollTimeoutRef.current);
    }

    // Debounce the scroll handling
    scrollTimeoutRef.current = setTimeout(() => {
      checkIfScrolledToBottom();
    }, 0); // 50ms debounce
  };

  useEffect(() => {
    window.addEventListener("scroll", handleScroll);

    return () => {
      window.removeEventListener("scroll", handleScroll);
      // Clean up timeout on unmount
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    };
  }, []);

  const streamingStatus = useAppSelector(
    (state) => state.mainForm.streamingStatus
  );

  // Add effect for initial check
  useEffect(() => {
    // Wait for content to be loaded and rendered
    const timer = setTimeout(() => {
      checkIfScrolledToBottom();
    }, 100);

    return () => clearTimeout(timer);
  }, [content, question, streamingStatus]); // Re-run when content or question changes

  const triggerScrollCheck = () => {
    checkIfScrolledToBottom();
  };

  const childProps = {
    ...props,
    triggerScrollCheck
  };

  const slugPageRendered = useAppSelector(
    (state) => state.mainForm.slugPageRendered
  );

  const askingQuestion = useAppSelector(
    (state) => state.mainForm.askingQuestion
  );

  const waitingForFirstChunk = useAppSelector(
    (state) => state.mainForm.waitingForFirstChunk
  );

  const answerErrorType = useAppSelector(
    (state) => state.mainForm.answerErrorType
  );
  const answerErrorExists = useAppSelector(
    (state) => state.mainForm.answerErrorExists
  );

  const postContentExist = useAppSelector(
    (state) => state.mainForm.postContentExist
  );

  const [input, setInput] = useState(null);

  const isBingeMapOpen = useAppSelector(
    (state) => state.mainForm.isBingeMapOpen
  );

  const toggleBingeMap = () => {
    dispatch(setIsBingeMapOpen(!isBingeMapOpen));
  };

  useEffect(() => {
    if (isBingeMapOpen) {
      // Just prevent scrolling while keeping position
      document.body.style.overflow = "hidden";
    } else {
      // Restore scrolling
      document.body.style.overflow = "";
    }

    return () => {
      // Cleanup
      document.body.style.overflow = "";
    };
  }, [isBingeMapOpen]);

  const [touchStart, setTouchStart] = useState(null);
  const [touchEnd, setTouchEnd] = useState(null);
  const slidePanel = useRef(null);

  // Minimum distance required for swipe
  const minSwipeDistance = 50;

  // Add a state to track if we're dragging the header
  const [isDraggingHeader, setIsDraggingHeader] = useState(false);

  // Modify touch handlers to only work on header
  const onTouchStart = (e) => {
    // Check if touch started on the header
    const header = e.target.closest(".flex-shrink-0");

    if (!header) return;

    setIsDraggingHeader(true);
    setTouchEnd(null);
    setTouchStart(e.targetTouches[0].clientY);
  };

  const onTouchMove = (e) => {
    // Only track movement if we started on header
    if (!isDraggingHeader) return;
    setTouchEnd(e.targetTouches[0].clientY);
  };

  const onTouchEnd = () => {
    if (!isDraggingHeader || !touchStart || !touchEnd) {
      setIsDraggingHeader(false);

      return;
    }

    const distance = touchStart - touchEnd;
    const isDownSwipe = distance < -minSwipeDistance;

    if (isDownSwipe) {
      dispatch(setIsBingeMapOpen(false));
    }

    setIsDraggingHeader(false);
  };

  const [sectionWidth, setSectionWidth] = useState(0);
  const [sectionLeft, setSectionLeft] = useState(0);
  const sectionRef = useRef(null);

  useEffect(() => {
    if (!sectionRef.current) return;

    const updateSectionMetrics = () => {
      const rect = sectionRef.current.getBoundingClientRect();

      setSectionWidth(rect.width);

      // Sadece küçük ekranlarda left pozisyonunu takip et
      if (windowWidth <= 1366) {
        setSectionLeft(rect.left);
      } else {
        setSectionLeft(0); // Büyük ekranlarda ortala
      }
    };

    const resizeObserver = new ResizeObserver(() => {
      updateSectionMetrics();
    });

    // Initial measurement
    updateSectionMetrics();
    resizeObserver.observe(sectionRef.current);

    // Window resize'ı da dinle
    window.addEventListener("resize", updateSectionMetrics);

    return () => {
      resizeObserver.disconnect();
      window.removeEventListener("resize", updateSectionMetrics);
    };
  }, []);

  // useEffect(() => {
  //   if (content && currentQuestionSlug && !isLoading && !streamingStatus) {
  //     fetchExampleQuestions(finalBingeId, currentQuestionSlug, questionText);
  //   }
  //   console.log("---exampleQuestions", exampleQuestions);
  // }, [content, currentQuestionSlug, isLoading, finalBingeId, streamingStatus]);

  // const fetchExampleQuestions = async (bingeId, slug, questionText) => {
  //   if (!slug || !content) return;

  //   try {
  //     const data = await getExampleQuestions(guruType, bingeId, slug, questionText);
  //     console.log("---fetchExampleQuestions data:", data);
  //     setExampleQuestions(data);
  //   } catch (error) {
  //     console.error("Error fetching example questions:", error);
  //     setExampleQuestions(["test"]);
  //   }
  // };

  const [submitTrigger, setSubmitTrigger] = useState(false);

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

  const handleFollowUpClick = useCallback(
    (question, e) => {
      dispatch(setInputValue(question));
      dispatch(setInputQuery(question));
      //console.log("dispatched follow up button question", question);
      setSubmitTrigger(true);
    },
    [dispatch, submitWithAbortController]
  );

  useEffect(() => {
    // Waits for the input value to be updated by the redux state by handleFollowUpClick, then submits
    // Run submitWithAbortController only if submitTrigger is true
    if (submitTrigger && inputValue) {
      setSubmitTrigger(false);
      submitWithAbortController(null, true); // Pass necessary arguments
    }
  }, [inputValue, submitTrigger]);

  const isAnswerValid = useAppSelector((state) => state.mainForm.isAnswerValid);
  const reduxSource = useAppSelector((state) => state.mainForm.source);
  const finalSource = reduxSource || source;

  const botTypes = [
    { name: "GitHub", type: "github" },
    { name: "Slack", type: "slack" },
    { name: "Discord", type: "discord" }
  ];

  console.log("finalSource", finalSource);
  const botType = botTypes.find(
    (bot) => bot.type === finalSource.toLowerCase()
  );

  const shouldHideFollowUp = botType !== undefined;

  const isSelfHosted = process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted";
  const { user } = isSelfHosted ? { user: true, isLoading: false } : useUser();

  const sessionUserExists = async () => {
    if (!user) {
      setShowLoginModal(true);

      return false;
    }

    return true;
  };

  // Modify the click handler to be async
  const handleExampleQuestionClick = async (question, e) => {
    const userExists = await sessionUserExists();

    if (userExists) {
      handleFollowUpClick(question, e);
    }
  };

  useBingeMap(guruType, finalBingeId);
  const treeData = useAppSelector((state) => state.mainForm.treeData);
  const bingeOutdated = useAppSelector((state) => state.mainForm.bingeOutdated);

  const [showFloatingSearch, setShowFloatingSearch] = useState(false);
  const [shouldShowSimilar, setShouldShowSimilar] = useState(false);

  useEffect(() => {
    // Only run on client-side
    if (typeof window !== "undefined") {
      setShowFloatingSearch(true);
      setShouldShowSimilar(!!slug);
    }
  }, [slug]);

  return (
    <main className="z-10 flex justify-center items-start px-6 guru-sm:px-0 w-full flex-grow guru-md:max-w-full polygon-fill">
      <div
        className={clsx(
          "grid grid-flow-col guru-xs:gap-0 gap-4 h-full w-full max-w-[1440px]",
          "xs:grid-cols-[112px_minmax(0,_1fr)] guru-md:grid-cols-[253px_minmax(112px,_1fr)] guru-lg:grid-cols-[253px_minmax(112px,_1fr)_253px]"
        )}>
        {/* OtherGurus section */}
        {windowWidth >= 768 && (
          <div className={clsx("guru-sm:hidden")}>
            <OtherGurus allGuruTypes={allGuruTypes} />
          </div>
        )}

        {/* Main content section */}
        <section
          ref={sectionRef}
          className="bg-white guru-sm:border-none border-l border-r border-solid border-neutral-200 flex-1 xs:col-span-2 guru-md:col-span-2">
          <section className="flex-1 flex flex-col h-full">
            <MainForm
              {...childProps}
              input={input}
              isScrolledToBottom={isScrolledToBottom}
              setContent={setContent}
              setDescription={setDescription}
              setInput={setInput}
              setQuestion={setQuestion}
            />
            {/* Sources section */}
            {!isLoading && !question && !content && resources?.length ? (
              <Sources
                guruTypeText={getGuruPromptMap(guruType, allGuruTypes)}
                resources={resources}
              />
            ) : null}
            {/* if question and content exist render PostContent in the page. Its for /slug page */}
            {slugPageRendered &&
              content &&
              !isLoading &&
              !streamingStatus &&
              !streamError &&
              !contextError &&
              isAnswerValid && (
                <AnswerLastModified
                  bingeId={finalBingeId}
                  initialDateUpdated={dateUpdated}
                />
              )}
            {!isLoading &&
              question &&
              content &&
              slugPageRendered &&
              !streamError &&
              !contextError &&
              isAnswerValid && (
                <PostContent
                  allGuruTypes={allGuruTypes}
                  content={content}
                  dateUpdated={dateUpdated}
                  description={description}
                  guruType={guruType}
                  isHelpful={isHelpful}
                  isScrolledToBottom={isScrolledToBottom}
                  question={question}
                  references={references}
                  similarQuestions={similarQuestions}
                  slug={slug}
                  trustScore={trustScore}
                />
              )}

            {typeof window !== "undefined" &&
              finalBingeId &&
              bingeOutdated &&
              !shouldHideFollowUp && (
                <div className="flex flex-col items-center justify-center gap-3 mt-auto mb-20">
                  <div className="w-12 h-12 rounded-full bg-slate-400 flex items-center justify-center">
                    <Clock className="w-8 h-8 text-white" />
                  </div>
                  <h1 className="text-2xl font-semibold">Oops</h1>
                  <p className="text-md text-muted-foreground text-center max-w-lg">
                    This binge has expired due to 2 hours of inactivity. You can
                    start a new binge.
                  </p>
                  <Button
                    className="gap-2 rounded-[24px]"
                    size="lg"
                    onClick={newQuestionClick}>
                    <Image
                      alt="New Question"
                      className="brightness-0 invert"
                      height={24}
                      src={NewQuestionIcon}
                      width={24}
                    />
                    New
                  </Button>
                </div>
              )}

            {typeof window !== "undefined" &&
              shouldHideFollowUp &&
              content &&
              !isLoading &&
              !streamingStatus &&
              !streamError &&
              !contextError &&
              isAnswerValid && (
                <div className="flex flex-col items-center justify-center gap-3 mt-auto mb-20">
                  <div className="w-12 h-12 rounded-full bg-slate-400 flex items-center justify-center">
                    <Clock className="w-8 h-8 text-white" />
                  </div>
                  <h1 className="text-2xl font-semibold">Bot Conversation</h1>
                  <p className="text-md text-muted-foreground text-center max-w-lg mx-4">
                    This binge is from a conversation on {botType?.name}. You
                    can't ask follow up questions.
                  </p>
                  <Button
                    className="gap-2 rounded-[24px]"
                    size="lg"
                    onClick={newQuestionClick}>
                    <Image
                      alt="New Question"
                      className="brightness-0 invert"
                      height={24}
                      src={NewQuestionIcon}
                      width={24}
                    />
                    New
                  </Button>
                </div>
              )}

            {/* <div className="w-full pt-16"></div> */}
            {typeof window !== "undefined" &&
              !bingeOutdated &&
              !shouldHideFollowUp &&
              content &&
              slug &&
              !isLoading &&
              !streamingStatus &&
              !streamError &&
              !contextError &&
              isAnswerValid && (
                <div
                  className="w-full border border-neutral-200 bg-neutral-50 mt-auto"
                  id="bottom-search-container">
                  <div className="w-full p-6 pb-8">
                    {/* Example Questions */}
                    <ExampleQuestions
                      questions={exampleQuestions}
                      onQuestionClick={handleExampleQuestionClick}
                    />

                    {/* Search Bar */}

                    <div className={clsx("flex items-center")}>
                      <div className="bg-white shadow-lg h-12 w-full rounded-full">
                        <FollowUpQueryInput
                          atBottom={true}
                          enableTypeSense={false}
                          error={error}
                          guruType={guruType}
                          guruTypePromptName={getGuruPromptMap(
                            guruType,
                            allGuruTypes
                          )}
                          inputId="bottom-search"
                          sessionUserExists={sessionUserExists}
                          setContentWrapperLeft={setContentWrapperLeft}
                          setContentWrapperWidth={setContentWrapperWidth}
                          setError={setError}
                          setTypesenseLoading={setTypesenseLoading}
                          onSubmit={(e) => {
                            // Unfocus input on submit
                            if (document.activeElement instanceof HTMLElement) {
                              document.activeElement.blur();
                            }
                            submitWithAbortController(e, true);
                          }}
                        />
                      </div>
                      <button
                        className="ml-2 bg-white text-black border border-gray-100 rounded-[8px] h-12 px-3 flex items-center gap-1.5"
                        onClick={newQuestionClick}>
                        <Image
                          alt="New Question"
                          height={24}
                          src={NewQuestionIcon}
                          width={24}
                        />

                        <span className="text-sm font-regular text-[#191919] guru-sm:hidden">
                          New
                        </span>
                      </button>
                    </div>
                  </div>
                </div>
              )}

            {/* Floating follow up search bar (present only with answer content) */}
            {typeof window !== "undefined" &&
              showFloatingSearch &&
              content &&
              !isBingeMapOpen &&
              !isLoading &&
              !streamingStatus &&
              !contextError &&
              isAnswerValid &&
              !bingeOutdated &&
              !shouldHideFollowUp && (
                <div
                  className={clsx(
                    "fixed",
                    "bottom-[0px]",
                    "pl-2 pr-2 guru-sm:pl-3 guru-sm:pr-3",
                    error ? "pb-12 guru-sm:pb-12" : "pb-8 guru-sm:pb-8",
                    "z-50",
                    "bg-gradient-to-b from-white/0 to-white",
                    isScrolledToBottom ? "hidden" : "block",
                    windowWidth > 1366 ? "left-1/2 -translate-x-1/2" : ""
                  )}
                  style={{
                    width: `${sectionWidth}px`,
                    // Sadece küçük ekranlarda left pozisyonunu kullan
                    ...(windowWidth <= 1366 ? { left: `${sectionLeft}px` } : {})
                  }}>
                  {typeof window !== "undefined" &&
                    !streamError &&
                    !contextError &&
                    isAnswerValid && (
                      <div className="max-w-[800px] mx-auto w-full">
                        <div className="flex items-center relative">
                          <div className="bg-white/80 shadow-lg h-12 w-full rounded-full">
                            <FollowUpQueryInput
                              enableTypeSense={false}
                              error={error}
                              guruType={guruType}
                              guruTypePromptName={getGuruPromptMap(
                                guruType,
                                allGuruTypes
                              )}
                              inputId="bottom-search"
                              sessionUserExists={sessionUserExists}
                              setContentWrapperLeft={setContentWrapperLeft}
                              setContentWrapperWidth={setContentWrapperWidth}
                              setError={setError}
                              setTypesenseLoading={setTypesenseLoading}
                              onSubmit={(e) => {
                                // Unfocus input on submit
                                if (
                                  document.activeElement instanceof HTMLElement
                                ) {
                                  document.activeElement.blur();
                                }
                                submitWithAbortController(e, true);
                              }}
                            />
                          </div>
                          <button
                            className="ml-2 bg-white text-gray-400 border border-solid border-gray-100 rounded-full p-2"
                            onClick={newQuestionClick}>
                            <Image
                              alt="New Question"
                              height={24}
                              src={NewQuestionIcon}
                              width={24}
                            />
                          </button>
                        </div>
                      </div>
                    )}
                </div>
              )}
            <CurrentlyAsking
              answerErrorType={answerErrorType}
              askingQuestion={askingQuestion}
              guruTypeName={getGuruPromptMap(guruType, allGuruTypes)}
              isLoading={isLoading}
              slugPageRendered={slugPageRendered}
              streamingStatus={streamingStatus}
              waitingForFirstChunk={waitingForFirstChunk}
            />
          </section>
        </section>

        {/* SimilarQuestions visible in guru-lg and above */}
        {
          <div
            className={clsx(
              shouldShowSimilar ? "guru-md:hidden guru-lg:block " : "hidden"
            )}>
            {!finalBingeId &&
              slugPageRendered &&
              content &&
              !isLoading &&
              !streamingStatus && (
                <SimilarQuestions similarQuestions={similarQuestions} />
              )}
            {finalBingeId && (
              <div className="flex flex-col items-start guru-md:justify-start rounded-lg flex-1 my-4 guru-sm:m-0 sticky guru-md:top-28 guru-lg:top-28 guru-sm:hidden h-[calc(100vh-170px)]">
                <BingeMap
                  bingeOutdated={bingeOutdated}
                  setContent={setContent}
                  setDescription={setDescription}
                  setQuestion={setQuestion}
                  treeData={treeData}
                />
              </div>
            )}
          </div>
        }
      </div>

      {/* Mobile Binge Map section */}
      {typeof window !== "undefined" && slug && (
        <>
          {treeData?.children?.length > 0 &&
            finalBingeId &&
            !isBingeMapOpen &&
            !isLoading &&
            !streamingStatus &&
            content &&
            slug && (
              <button
                className={clsx(
                  "guru-lg:hidden fixed right-8 z-50 transition-all duration-300",
                  bingeOutdated ? "bottom-10" : "bottom-32"
                )}
                onClick={toggleBingeMap}>
                <Image
                  alt="Binge Map"
                  className="transition-transform"
                  height={50}
                  src={BingeMapIcon}
                  width={50}
                />
              </button>
            )}

          {/* Mobile Binge Map Sliding Panel */}
          {finalBingeId &&
            !isLoading &&
            !streamingStatus &&
            content &&
            slug && (
              <div
                ref={slidePanel}
                className={`guru-lg:hidden fixed bottom-0 left-0 right-0 border-t border-neutral-200 transition-transform duration-300 ease-in-out z-40 overflow-hidden bg-white ${
                  isBingeMapOpen ? "translate-y-0" : "translate-y-full"
                }`}
                style={{
                  height: "70vh",
                  borderTopLeftRadius: "20px",
                  borderTopRightRadius: "20px"
                }}
                onTouchEnd={onTouchEnd}
                onTouchMove={onTouchMove}
                onTouchStart={onTouchStart}>
                <div className="flex flex-col h-full bg-white">
                  {/* Header - Draggable for mobile, Close button for desktop */}
                  <div className="p-3 flex-shrink-0 flex justify-center items-center bg-white">
                    {windowWidth < 768 ? ( // window.innerWidth yerine windowWidth
                      <div className="w-12 h-1.5 bg-neutral-300 rounded-full cursor-grab active:cursor-grabbing" />
                    ) : (
                      // Close button for desktop
                      <button
                        aria-label="Close binge map"
                        className="absolute right-4 top-4 p-2 hover:bg-neutral-100 rounded-full transition-colors"
                        onClick={() => dispatch(setIsBingeMapOpen(false))}>
                        <X className="h-5 w-5 text-neutral-500" />
                      </button>
                    )}
                  </div>

                  {/* Scrollable content - will not trigger panel close */}
                  <div className="flex-1 overflow-y-auto overscroll-contain">
                    <div className="h-full p-4">
                      <BingeMap
                        bingeOutdated={bingeOutdated}
                        setContent={setContent}
                        setDescription={setDescription}
                        setQuestion={setQuestion}
                        treeData={treeData}
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}

          {/* Overlay */}
          {isBingeMapOpen && (
            <div
              className="guru-lg:hidden fixed inset-0 bg-black/50 z-30"
              onClick={toggleBingeMap}
            />
          )}
        </>
      )}
    </main>
  );
};

export default Content;
