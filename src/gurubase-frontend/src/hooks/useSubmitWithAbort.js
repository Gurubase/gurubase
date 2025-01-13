import { useRouter } from "next/navigation";
import { useAppDispatch, useAppSelector } from "@/redux/hooks";
import { useHandleSubmit } from "@/hooks/useHandleSubmit";
import {
  setStreamError,
  setIsLoading,
  setContextError,
  setQuestionText,
  setRootSlug,
  setInvalidAnswer,
  setValidAnswer,
  setBingeId,
  setBingeMapRefreshTrigger
} from "@/redux/slices/mainFormSlice";
import { createBinge } from "@/app/actions";

export const useSubmitWithAbort = (
  guruType,
  setInput,
  checkErrorExist,
  setError,
  triggerStreamUpdate,
  setContent,
  setQuestion,
  setDescription,
) => {
  const dispatch = useAppDispatch();
  const getState = useAppSelector;
  const handleSubmit = useHandleSubmit(
    guruType,
    checkErrorExist,
    setError,
    triggerStreamUpdate,
    setContent,
    setQuestion,
    setDescription,
  );

  const currentQuestionSlug = useAppSelector(
    (state) => state.mainForm.currentQuestionSlug
  );

  const bingeId = useAppSelector((state) => state.mainForm.bingeId);
  const inputValue = useAppSelector((state) => state.mainForm.inputValue);
  const rootSlug = useAppSelector((state) => state.mainForm.rootSlug);

  const submitWithAbortController = async (e, isFollowUp = false) => {
    //console.log("submit with abort controller");
    const controller = new AbortController();
    // dispatch(setIsLoading(true));

    // dispatch(setStreamError(false));
    // dispatch(setContextError(false));
    dispatch(setQuestionText(inputValue));
    //console.log("setting valid answer to true");
    dispatch(setValidAnswer(true));
    dispatch(setInvalidAnswer(null));
    dispatch(setStreamError(false));
    dispatch(setContextError(false));

    //console.log("submit with abort controller");
    let rootSlugToUse;
    if (isFollowUp) {
      let newBinge = false;
      //console.log("is follow up");
      let newBingeId;
      if (!bingeId) {
        newBingeId = await createBinge({
          guruType,
          rootSlug: currentQuestionSlug
        });
        if (!newBingeId) {
          throw new Error("Failed to initialize binge session");
        }
        dispatch(setBingeId(newBingeId));
        newBinge = true;
        dispatch(setRootSlug(currentQuestionSlug));
        rootSlugToUse = currentQuestionSlug;

        // Force refresh binge map data by setting a refresh trigger in Redux
        dispatch(setBingeMapRefreshTrigger(Date.now()));
      } else {
        rootSlugToUse = rootSlug;
      }
      newBingeId = bingeId ? bingeId : newBingeId; // If not updated yet

      // For follow-up queries, don't navigate
      try {
        dispatch(setIsLoading(true));
        //console.log("set is loading to true");
        await handleSubmit(
          e,
          controller.signal,
          isFollowUp,
          inputValue,
          newBingeId,
          newBinge,
          rootSlugToUse
        );
      } catch (error) {
        //console.log("error", error);
        dispatch(
          setStreamError({
            status: error.status || 500,
            message: error.message
          })
        );
        //console.log("set stream error");
        dispatch(setIsLoading(false));
        //console.log("Set is loading to false");
      }
    } else {
      // For initial queries, use existing logic with navigation
      setInput(e);
      //console.log("set input");
    }

    return () => controller.abort();
  };

  return submitWithAbortController;
};
