import * as Sentry from "@sentry/nextjs";
import { isbot } from "isbot";
import { cookies, headers } from "next/headers";
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
    let answerValid = null;
    let resultNoIndex = null;
    let questionCookieSummaryMatch = true;
    let dateCreated = null;
    let dateUpdated = null;

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

      if (streamSlug !== params.slug) {
        questionCookieSummaryMatch = false; // if slug in the cookie and slug in the params does not match

        if (params.slug) {
          // if slug exists in the params
          //console.log("binge id is null");
          const response = await getDataForSlugDetails(
            // get data for the slug from the backend and set it them as metadata
            params.slug,
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
          new Error(`Answer is not valid for slug:${params.slug}`)
        );
      }
    } else if (params.slug && !searchParams.question) {
      // if only slug exists in the params and question not exists in the searchParams
      try {
        //console.log("binge id is null");
        const response = await getDataForSlugDetails(
          params.slug,
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
            og_image_url: instantOgImage,
            date_created_meta: instantDateCreated,
            date_updated_meta: instantDateUpdated
          } = JSON.parse(response);

          question = instantQuestion;
          description = instantDescription;
          resultNoIndex = instantNoIndex;
          guruTypeOgImage = instantOgImage;
          dateCreated = instantDateCreated;
          dateUpdated = instantDateUpdated;
        }
      } catch (error) {
        // console.error("error in generateMetadata", error);
        notFound();
      }
    }

    if (question && description) {
      const canonicalUrl = `${process.env.NEXT_PUBLIC_PROJECT_URL}g/${params.guruType}/${params.slug}`;

      return {
        title: question + " | Gurubase",
        description: description,
        openGraph: {
          title: question + " | Gurubase",
          description: description,
          images: guruTypeOgImage || mainOgImage,
          url: canonicalUrl,
          type: "article",
          publishedTime: dateCreated,
          modifiedTime: dateUpdated,
          section: params.guruType,
          tags: [params.guruType]
        },
        robots: {
          index: resultNoIndex ? false : true
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
  // Early return for missing slug
  if (!params.slug) {
    return redirect(`/not-found`);
  }

  // Get all data first
  const [response, allGuruTypes] = await Promise.all([
    getDataForSlugDetails(params.slug, params.guruType, null, searchParams.question),
    getGuruTypes()
  ]);

  const parsedResponse = JSON.parse(response);
  const { msg: responseMsg } = parsedResponse;

  // Handle invalid guru type
  if (responseMsg?.toLowerCase() === "guru type is invalid.") {
    notFound();
  }

  const {
    msg,
    question,
    content,
    description,
    references,
    similar_questions,
    trust_score,
    dirty,
    date_updated
  } = parsedResponse;

  const headersList = headers();
  const userAgent = headersList.get("user-agent") || "";
  const isBot = isbot(userAgent);

  const reload = dirty && !isBot;
  const isInstantContentExist = !(response && msg?.toLowerCase() === "question not found") && !reload;
  const exampleQuestions = [];

  return (
    <ResultClient
      allGuruTypes={allGuruTypes || []}
      dateUpdated={isInstantContentExist ? date_updated : null}
      dirty={reload}
      exampleQuestions={exampleQuestions}
      guruType={params.guruType}
      instantContent={isInstantContentExist ? content : null}
      instantDescription={description}
      instantQuestion={question}
      isHelpful={true}
      references={references}
      similarQuestions={isInstantContentExist ? similar_questions : []}
      slug={params.slug}
      trustScore={trust_score}
    />
  );
};

export default Result;
