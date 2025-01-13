import {
  setCurrentQuestionSlug,
  setParentQuestionSlug,
  setQuestionUpdate
} from "@/redux/slices/mainFormSlice";

export const bingeRedirection = async ({
  dispatch,
  newSlug,
  oldSlug,
  followUp = true,
  questionText,
  guruType,
  bingeId,
  trustScore,
  dateUpdated,
  references,
  followUpQuestions = []
}) => {
  // console.log("bingeRedirection");

  // Create URL with query parameters
  if (bingeId) {
    // Otherwise it is an initial question
    const searchParams = new URLSearchParams();
    searchParams.append("question_slug", newSlug);

    // Get root slug from URL or fallback to oldSlug
    const currentPath = window.location.pathname;
    //console.log("currentPath", currentPath);
    const rootSlug = currentPath.startsWith(`/g/${guruType}/`)
      ? currentPath.split("/")[3]
      : oldSlug;

    // Construct the new URL
    const newUrl = `/g/${guruType}/${rootSlug}/binge/${bingeId}${
      searchParams.toString() ? `?${searchParams.toString()}` : ""
    }`;

    // Update URL without triggering re-render
    window.history.pushState(null, "", newUrl);
    //console.log("redirected to new slug with params:", newUrl);
  }

  dispatch(setQuestionUpdate({ trustScore, dateUpdated, references, followUpQuestions }));

  // Update slugs in Redux store
  dispatch(setCurrentQuestionSlug(newSlug));
  //console.log("set current question slug", newSlug);

  if (followUp) {
    dispatch(setParentQuestionSlug(oldSlug));
    //console.log("set parent question slug", oldSlug);
  }

  //console.log("done with binge redirection");
};
