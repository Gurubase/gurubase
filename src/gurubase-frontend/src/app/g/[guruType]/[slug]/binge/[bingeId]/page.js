import * as Sentry from "@sentry/nextjs";
import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";

import { getDataForSlugDetails, getGuruTypes } from "@/app/actions";
import { ResultClient } from "@/components/ResultClient";

export async function generateMetadata(context) {
  const { params, searchParams } = context;
  let mainOgImage =
    "https://s3.eu-central-1.amazonaws.com/anteon-strapi-cms-wuby8hpna3bdecoduzfibtrucp5x/Og_image_06c9ac418a.png";

  let guruTypeOgImage = null;

  try {
    let question = null;
    let description = null;
    let error = null;
    let answerValid = null;
    let resultNoIndex = null;
    let questionCookieSummaryMatch = true;

    // if question exists in the searchParams
    if (searchParams.question) {
      const cookieStore = cookies();

      const questionCookieSummary = cookieStore.get("questionSummary"); // get questionSummary cookie

      const {
        question: streamQuestion,
        description: streamDescription,
        answerValid: streamAnswerValid,
        noindex: streamNoIndex,
        question_slug: streamSlug
      } = JSON.parse(questionCookieSummary.value);

      if (streamSlug !== searchParams.question_slug) {
        questionCookieSummaryMatch = false; // if slug in the cookie and slug in the params does not match

        if (searchParams.question_slug) {
          // if slug exists in the params
          //console.log("binge id is null");
          const response = await getDataForSlugDetails(
            // get data for the slug from the backend and set it them as metadata
            searchParams.question_slug,
            params.guruType,
            params.bingeId,
            searchParams.question
          );
          const { msg } = JSON.parse(response);

          if (msg?.toLowerCase() === "guru type is invalid.") {
            notFound();
          }
          if (response) {
            const {
              question: instantQuestion,
              description: instantDescription,
              noindex: instantNoIndex
            } = JSON.parse(response);

            question = instantQuestion;
            description = instantDescription;
            resultNoIndex = instantNoIndex;
          }
        }
      }
      if (questionCookieSummaryMatch) {
        question = streamQuestion;
        description = streamDescription;
        answerValid = streamAnswerValid;
        resultNoIndex = streamNoIndex;
      }

      if (!answerValid) {
        // send to sentry if answer is not valid
        Sentry.captureException(
          new Error(
            `Answer is not valid for slug:${searchParams.question_slug}`
          )
        );
      }
    } else if (searchParams.question_slug && !searchParams.question) {
      // if only slug exists in the params and question not exists in the searchParams
      try {
        //console.log("binge id is null");
        const response = await getDataForSlugDetails(
          searchParams.question_slug,
          params.guruType,
          null,
          searchParams.question
        );

        const { msg } = JSON.parse(response);

        if (msg?.toLowerCase() === "guru type is invalid.") {
          notFound();
        }
        if (response) {
          const {
            question: instantQuestion,
            description: instantDescription,
            noindex: instantNoIndex,
            og_image_url: instantOgImage
          } = JSON.parse(response);

          question = instantQuestion;
          description = instantDescription;
          resultNoIndex = instantNoIndex;
          guruTypeOgImage = instantOgImage; // when instant quesiton response has og:image specific to question use it
        }
      } catch (error) {
        // console.error("error in generateMetadata", error);
        notFound();
      }
    }

    if (question && description) {
      const canonicalUrl = `${process.env.NEXT_PUBLIC_PROJECT_URL}g/${params.guruType}/${searchParams.question_slug}`;

      return {
        title: question + " | Gurubase",
        description: description,
        openGraph: {
          title: question + " | Gurubase",
          description: description,
          images: guruTypeOgImage || mainOgImage,
          url: canonicalUrl
        },
        robots: {
          index: false
        },
        alternates: {
          canonical: canonicalUrl
        }
      };
    }
  } catch (error) {
    // redirecto to 404 page
    // console.error("error in generateMetadata", error);
  }
}

const Result = async ({ params, searchParams }) => {
  if (!searchParams.question_slug) {
    return redirect(`/not-found`);
  }

  //console.log("Using bingeId:", params.bingeId);
  const response = await getDataForSlugDetails(
    searchParams.question_slug,
    params.guruType,
    params.bingeId, // Pass bingeId to the function
    searchParams.question
  );

  const { msg: responseMsg } = JSON.parse(response);

  if (responseMsg?.toLowerCase() === "guru type is invalid.") {
    notFound();
  }

  // get guru types
  const allGuruTypes = await getGuruTypes();

  const {
    msg,
    question,
    content,
    description,
    references,
    similar_questions,
    date_updated,
    trust_score
  } = JSON.parse(response);

  const isInstantContentExist = !(
    response && msg?.toLowerCase() === "question not found"
  );

  if (msg?.toLowerCase() === "guru type is invalid.") {
    return redirect(`/not-found`);
  }

  return (
    <ResultClient
      allGuruTypes={allGuruTypes || []}
      dateUpdated={date_updated}
      guruType={params.guruType}
      instantContent={isInstantContentExist ? content : null}
      instantDescription={description}
      instantQuestion={question}
      isHelpful={true}
      passedBingeId={params.bingeId} // Pass bingeId to ResultClient
      references={references}
      similarQuestions={isInstantContentExist ? similar_questions : []}
      slug={searchParams.question_slug}
      trustScore={trust_score}
    />
  );
};

export default Result;
