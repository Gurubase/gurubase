// redux/slices/counterSlice.js
import { createSlice, createAction } from "@reduxjs/toolkit";

// NOTE: If you add initial state to slice, also add to reset action
const initialState = {
  isLoading: false,
  defaultQuestionSelection: null,
  questionSummary: null,
  postContentExist: false,
  inputValue: "",
  invalidAnswer: null,
  inputQuery: null,
  streamingStatus: false,
  mobileInputFocused: false,
  panelHintsListed: false,
  slugPageRendered: true, // to understand if the page is rendered again or not
  activeGuruName: null,
  streamError: false,
  contextError: false,
  isBingeMapOpen: false,
  currentQuestionSlug: null,
  parentQuestionSlug: null,
  bingeId: null,
  questionText: null,
  rootSlug: "",
  validAnswer: true,
  hasFetched: false,
  references: [],
  isPageTransitioning: false,
  bingeOutdated: false,
  bingeMapRefreshTrigger: null,
  askingQuestion: false, // We are sending /summary/ and /answer/ requests to the backend
  waitingForFirstChunk: false,
  isAnswerValid: true,
  answerErrorType: null,
  trustScore: null,
  dateUpdated: null,
  followUpQuestions: [],
  treeData: null,
  bingeOutdated: false
};

const mainFormSlice = createSlice({
  name: "mainForm",
  initialState: initialState,
  reducers: {
    setBingeInfo: (state, action) => {
      state.treeData = action.payload.treeData;
      state.bingeOutdated = action.payload.bingeOutdated;
    },
    setFollowUpQuestions: (state, action) => {
      state.followUpQuestions = action.payload;
    },
    setQuestionUpdate: (state, action) => {
      state.trustScore = action.payload.trustScore;
      state.dateUpdated = action.payload.dateUpdated;
      state.references = action.payload.references;
      if (Array.isArray(action.payload.followUpQuestions)) {
        state.followUpQuestions = action.payload.followUpQuestions;
      } else {
        state.followUpQuestions = [];
      }
    },
    setBingeOutdated: (state, action) => {
      state.bingeOutdated = action.payload;
    },
    setHasFetched: (state, action) => {
      state.hasFetched = action.payload;
    },
    setValidAnswer: (state, action) => {
      state.validAnswer = action.payload;
    },
    setRootSlug: (state, action) => {
      state.rootSlug = action.payload;
    },
    setQuestionText: (state, action) => {
      state.questionText = action.payload;
    },
    setParentQuestionSlug: (state, action) => {
      //console.log("---|in redux set parent question slug", action.payload);
      state.parentQuestionSlug = action.payload;
    },
    resetErrors: (state) => {
      state.isAnswerValid = true;
      state.contextError = false;
      state.streamError = false;
    },
    setAnswerError: (state, action) => {
      // Sets the error type and shows the error for 700ms
      state.answerErrorType = action.payload;
    },
    setIsAnswerValid: (state, action) => {
      state.isAnswerValid = action.payload;
    },
    setWaitingForFirstChunk: (state, action) => {
      state.waitingForFirstChunk = action.payload;
    },
    setAskingQuestion: (state, action) => {
      state.askingQuestion = action.payload;
    },
    setIsLoading: (state, action) => {
      state.isLoading = action.payload;
    },
    setDefaultQuestionToInput: (state, action) => {
      state.defaultQuestionSelection = action.payload;
    },
    // setQuestionSummary action.payload will be json object
    setQuestionSummary: (state, action) => {
      state.questionSummary = action.payload;
    },
    setPostContentExist: (state, action) => {
      state.postContentExist = action.payload;
    },
    setInputValue: (state, action) => {
      state.inputValue = action.payload;
    },
    setInvalidAnswer: (state, action) => {
      state.invalidAnswer = action.payload;
    },
    setInputQuery: (state, action) => {
      //console.log("---|in redux set input query", action.payload);
      state.inputQuery = action.payload;
      if (action.payload) {
        state.defaultQuestionSelection = null;
      }
    },
    setStreamingStatus: (state, action) => {
      state.streamingStatus = action.payload;
    },
    setMobileInputFocused: (state, action) => {
      state.mobileInputFocused = action.payload;
    },
    setPanelHintsListed: (state, action) => {
      state.panelHintsListed = action.payload;
    },
    setSlugPageRendered: (state, action) => {
      state.slugPageRendered = action.payload;
    },
    setActiveGuruName: (state, action) => {
      state.activeGuruName = action.payload;
    },
    setStreamError: (state, action) => {
      state.streamError = action.payload;
    },
    setResetMainForm: (state) => {
      state.isLoading = false;
      state.defaultQuestionSelection = null;
      state.questionSummary = null;
      state.postContentExist = false;
      state.inputValue = "";
      state.invalidAnswer = null;
      state.inputQuery = null;
      state.streamingStatus = null;
      state.mobileInputFocused = false;
      state.panelHintsListed = false;
      state.slugPageRendered = true;
      state.activeGuruName = null;
      state.streamError = false;
      state.askingQuestion = false;
    },
    setContextError: (state, action) => {
      state.contextError = action.payload;
    },
    setIsBingeMapOpen: (state, action) => {
      state.isBingeMapOpen = action.payload;
    },
    resetInputValue: (state) => {
      state.inputValue = "";
    },
    setCurrentQuestionSlug: (state, action) => {
      state.currentQuestionSlug = action.payload;
    },
    setBingeId: (state, action) => {
      state.bingeId = action.payload;
    },
    setPageTransitioning: (state, action) => {
      state.isPageTransitioning = action.payload;
    },
    setBingeMapRefreshTrigger: (state, action) => {
      state.bingeMapRefreshTrigger = action.payload;
    }
  }
});

export const {
  setIsLoading,
  setDefaultQuestionToInput,
  setQuestionSummary,
  setPostContentExist,
  setInputValue,
  setInvalidAnswer,
  setInputQuery,
  setResetMainForm,
  setStreamingStatus,
  setMobileInputFocused,
  setPanelHintsListed,
  setSlugPageRendered,
  setActiveGuruName,
  setStreamError,
  setContextError,
  setParentQuestionSlug,
  setIsBingeMapOpen,
  resetInputValue,
  setCurrentQuestionSlug,
  setBingeId,
  setQuestionText,
  setRootSlug,
  setValidAnswer,
  setHasFetched,
  setPageTransitioning,
  setBingeOutdated,
  setBingeMapRefreshTrigger,
  setAskingQuestion,
  setWaitingForFirstChunk,
  setIsAnswerValid,
  setAnswerError,
  resetErrors,
  setQuestionUpdate,
  setFollowUpQuestions,
  setBingeInfo
} = mainFormSlice.actions;
export default mainFormSlice.reducer;
