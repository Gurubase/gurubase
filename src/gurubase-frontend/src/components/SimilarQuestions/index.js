import { useParams } from "next/navigation";
import React, { useEffect, useState } from "react";

import { useAppSelector } from "@/redux/hooks";

import QuestionItem from "./QuestionItem";

const SimilarQuestions = ({ isMobile, similarQuestions }) => {
  const { slug } = useParams();
  const [questions, setQuestions] = useState(similarQuestions || []);

  const reduxSimilarQuestions = useAppSelector(
    (state) => state.mainForm.similar_questions
  );

  useEffect(() => {
    if (Array.isArray(reduxSimilarQuestions) && reduxSimilarQuestions.length) {
      const sortedQuestions = [...reduxSimilarQuestions].sort(
        (a, b) => a.distance - b.distance
      );

      setQuestions(sortedQuestions);
      return;
    }

    if (Array.isArray(similarQuestions) && similarQuestions.length) {
      const sortedQuestions = [...similarQuestions].sort(
        (a, b) => a.distance - b.distance
      );

      setQuestions(sortedQuestions);
    }
  }, [similarQuestions, reduxSimilarQuestions]);

  if (!questions?.length) return null;

  return (
    <section
      className={`${
        isMobile ? "hidden guru-md:flex similar-questions" : "guru-md:hidden"
      } flex guru-lg:sticky guru-lg:top-28 guru-md:relative flex-col font-medium bg-white rounded-[8px] border border-solid border-gray-85 flex-1 guru-md:overflow-hidden  my-4 text-zinc-900 max-h-[calc(100vh-170px)] guru-md:max-h-full ${
        !slug && "opacity-0"
      } guru-md:border-none`}>
      <span className="flex gap-2.5 px-3 py-5 w-full rounded-t-xl text-base font-medium bg-white border-solid border-b-[0.5px] border-b-neutral-200 min-h-[56px] text-zinc-900 guru-sm:hidden">
        Related
      </span>
      <div className="flex guru-md:gap-2.5 z-0 flex-col guru-md:flex-row guru-lg:items-start guru-md:rounded-b-none rounded-b-lg overflow-y-scroll overflow-x-hidden guru-lg:featured-scrollbar max-h-[calc(100vh-170px)] mt-2 guru-md:pb-2 w-full text-sm guru-md:overflow-x-scroll guru-md:max-w-full guru-md:max-h-full guru-md:items-start">
        {questions
          .filter(
            (question, index, self) =>
              index === self.findIndex((q) => q.title === question.title)
          )
          ?.map((question, index) => (
            <React.Fragment key={question.id}>
              <QuestionItem
                isLast={!isMobile && index === questions.length - 1}
                isMobile={isMobile}
                slug={question?.slug}
                text={question.title}
              />
            </React.Fragment>
          ))}
      </div>
    </section>
  );
};

export default SimilarQuestions;
