import { getDataForSlugDetails } from "@/app/actions";
import {
  setInputQuery,
  setInputValue,
  setPageTransitioning
} from "@/redux/slices/mainFormSlice";
import { bingeRedirection } from "@/utils/bingeRedirection";

export const handleQuestionUpdate = async ({
  guruType,
  newSlug,
  oldSlug,
  dispatch,
  setContent,
  setQuestion,
  setDescription,
  bingeId,
  questionText,
  content = null,
  question = null,
  description = null,
  references = [],
  trustScore = null,
  dateUpdated = null,
  followUpQuestions = []
}) => {
  try {
    dispatch(setPageTransitioning(true));

    if (content === null || question === null || description === null) {
      const response = await getDataForSlugDetails(
        newSlug,
        guruType,
        bingeId,
        questionText
      );
      const data = JSON.parse(response);

      content = data.content;
      question = data.question;
      description = data.description;
      references = data.references;
      trustScore = data.trust_score;
      dateUpdated = data.date_updated;
      followUpQuestions = data.follow_up_questions;
    }

    setContent(content);
    setQuestion(question);
    setDescription(description);

    await bingeRedirection({
      dispatch,
      newSlug,
      oldSlug,
      followUp: false,
      questionText,
      guruType,
      bingeId,
      trustScore,
      dateUpdated,
      references,
      followUpQuestions
    });

    dispatch(setInputQuery(""));
    dispatch(setInputValue(""));

    window.scrollTo({
      top: 0
    });
  } catch (error) {
    // console.error("Error in handleQuestionUpdate:", error);
  } finally {
    dispatch(setPageTransitioning(false));
  }
};
