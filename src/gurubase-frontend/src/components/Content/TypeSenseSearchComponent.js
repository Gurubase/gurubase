"use client";

import "@algolia/autocomplete-theme-classic";

import { autocomplete } from "@algolia/autocomplete-js";
import { useParams } from "next/navigation";
import { useEffect } from "react";
import Typesense from "typesense";

import { useAppDispatch, useAppSelector } from "@/redux/hooks";
import {
  setInputQuery,
  setInputValue,
  setPanelHintsListed,
  setResetMainForm
} from "@/redux/slices/mainFormSlice";

const TypeSenseSearchComponent = ({
  handleRedirectToSlugPage,
  guruType,
  guruTypePromptName
}) => {
  const dispatch = useAppDispatch();
  const defaultQuestionSelection = useAppSelector(
    (state) => state.mainForm.defaultQuestionSelection
  );

  const { slug } = useParams();

  const inputQuery = useAppSelector((state) => state.mainForm.inputQuery);

  useEffect(() => {
    if (typeof window === "undefined") return;

    let typesenseClient;

    if (process.env.NEXT_PUBLIC_NODE_ENV !== "selfhosted") {
      typesenseClient = new Typesense.Client({
        apiKey: process.env.NEXT_PUBLIC_TYPESENSE_SEARCH_ONLY_API_KEY,
        nodes: [
          {
            host: process.env.NEXT_PUBLIC_TYPESENSE_HOST,
            port: parseInt(process.env.NEXT_PUBLIC_TYPESENSE_PORT),
            protocol: process.env.NEXT_PUBLIC_TYPESENSE_PROTOCOL
          }
        ],
        additionalSearchParameters: {
          query_by: "question",
          num_typos: 2
        },
        connectionTimeoutSeconds: 8
      });
    }

    if (
      document.querySelector("#autocomplete") &&
      document.querySelectorAll("#autocomplete")?.length > 1
    ) {
      document.querySelector("#autocomplete").innerHTML = "";
    }

    if (document.querySelector("#autocomplete")) {
      const { setQuery, refresh, setIsOpen } = autocomplete({
        container: "#autocomplete",
        placeholder: `Ask anything about ${guruTypePromptName}`,
        detachedMediaQuery: "none",
        debug: false,

        async getSources({ query }) {
          dispatch(setInputValue(query));
          if (process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted") {
            return [
              {
                sourceId: "predictions",
                getItems() {
                  return [];
                },
                onSelect() {},
                getItemInputValue() {
                  return "";
                },
                templates: {
                  item() {
                    return "";
                  }
                }
              }
            ];
          }
          try {
            const results = await typesenseClient
              .collections(`${guruType}`)
              .documents()
              .search({
                q: query,
                query_by: "question",
                highlight_full_fields: "question",
                highlight_start_tag: "|guruBS|",
                highlight_end_tag: "|guruBE|",
                per_page: window.innerWidth <= 915 ? 3 : 5
              });

            return [
              {
                sourceId: "predictions",
                getItems() {
                  return results.hits.filter(
                    (hit) => hit.document.slug !== slug
                  );
                },
                onSelect(event) {
                  if (event?.item?.document?.slug) {
                    handleRedirectToSlugPage(event.item.document.slug);
                    // dispatch(setInputQuery(event.item.document.question));
                    dispatch(setResetMainForm());
                  }
                },
                getItemInputValue({
                  item: {
                    document: { question }
                  }
                }) {
                  return `${question}`;
                },
                templates: {
                  item({ item, html }) {
                    let question =
                      item.highlights.find((h) => h.field === "question")
                        ?.value || item.document["question"];

                    if (question.includes("`")) {
                      question = question
                        .replaceAll(">`", "&gt;")
                        .replaceAll("`<", "&lt;");
                    }
                    question = question
                      .replaceAll("|guruBS|", "<b class='text-anteon-orange'>")
                      .replaceAll("|guruBE|", "</b>");
                    const html_fragment = html`${question}`;

                    return html`<div
                      dangerouslySetInnerHTML=${{
                        __html: html_fragment
                      }}></div>`;
                  }
                }
              }
            ];
          } catch {
            return [
              {
                sourceId: "predictions",
                getItems() {
                  return [];
                },
                onSelect() {},
                getItemInputValue() {
                  return "";
                },
                templates: {
                  item() {
                    return "";
                  }
                }
              }
            ];
          }
        },
        async onStateChange({ state }) {
          if (!state.query) {
            dispatch(setInputQuery(null));
          }
        }
      });

      // Manually reset the state on clear button click
      const clearButton = document.querySelector(".aa-ClearButton");

      clearButton?.addEventListener("click", () => {
        setIsOpen(false);
        document.querySelector(".aa-Input")?.focus();
        dispatch(setPanelHintsListed(false));
      });

      setQuery(inputQuery || defaultQuestionSelection);
      refresh();
    }

    return () => {
      if (document.querySelector("#autocomplete")) {
        document.querySelector("#autocomplete").innerHTML = "";
      }
    };
  }, [dispatch, setInputValue, inputQuery, defaultQuestionSelection]);

  return (
    <div
      className="flex-1 self-stretch my-auto xs:max-w-ful xs:py-2 py-2 min-h-[60px]"
      id="autocomplete"></div>
  );
};

export default TypeSenseSearchComponent;
