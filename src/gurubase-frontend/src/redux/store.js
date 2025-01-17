// redux/store.js
import { configureStore } from "@reduxjs/toolkit";
import mainFormReducer from "./slices/mainFormSlice";

export const makeStore = () => {
  return configureStore({
    reducer: {
      mainForm: mainFormReducer
    },
    middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(),
    devTools: process.env.NEXT_PUBLIC_NODE_ENV !== "production"
  });
};
