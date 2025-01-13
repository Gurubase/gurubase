import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { setAnswerError } from "@/redux/slices/mainFormSlice";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export const getNormalizedDomain = (url) => {
  try {
    const hostname = new URL(url).hostname;
    return hostname.replace(/^www\./, "");
  } catch (error) {
    return null;
  }
};

export const setAnswerErrorWithTimeout = async (dispatch, answerErrorType) => {
  try {
    dispatch(setAnswerError(answerErrorType));

    return new Promise((resolve) => {
      setTimeout(() => {
        try {
          dispatch(setAnswerError(null));
          resolve();
        } catch (error) {
          // console.error("[Timeout] Error:", error);
          resolve();
        }
      }, 700);
    });
  } catch (error) {
    // console.error("[Error] setAnswerErrorWithTimeout:", error);
  }
};
