"use client";

import { useEffect } from "react";
import { useAppDispatch } from "@/redux/hooks";
import {
  setCurrentQuestionSlug,
  setParentQuestionSlug,
  setBingeOutdated,
  setBingeId
} from "@/redux/slices/mainFormSlice";

export default function GuruTypeInitializer() {
  const dispatch = useAppDispatch();

  useEffect(() => {
    dispatch(setBingeId(null));
    dispatch(setCurrentQuestionSlug(null));
    dispatch(setParentQuestionSlug(null));
    dispatch(setBingeOutdated(false));
  }, [dispatch]);

  return null;
}
