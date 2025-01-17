export const formatDate = (dateString) => {
  // TODO: ToLocale kismini sil
  return new Date(dateString).toLocaleDateString("en-US", {
    day: "numeric",
    month: "short",
    year: "numeric"
  });
};
