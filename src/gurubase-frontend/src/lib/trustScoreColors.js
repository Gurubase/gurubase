/**
 * Get background and text colors based on a trust score
 * @param {number} score - Trust score value between 0-100
 * @returns {{ bg: string, text: string }} Color classes for background and text
 */
export const getColors = (score) => {
  if (score >= 90) return { bg: "bg-emerald-500", text: "text-emerald-500" };
  if (score >= 80) return { bg: "bg-green-500", text: "text-green-500" };
  if (score >= 70) return { bg: "bg-lime-500", text: "text-lime-500" };
  if (score >= 60) return { bg: "bg-yellow-500", text: "text-yellow-500" };
  if (score >= 50) return { bg: "bg-orange-400", text: "text-orange-400" };
  if (score >= 40) return { bg: "bg-orange-500", text: "text-orange-500" };
  if (score >= 30) return { bg: "bg-red-400", text: "text-red-400" };
  if (score >= 20) return { bg: "bg-red-500", text: "text-red-500" };

  return { bg: "bg-red-600", text: "text-red-600" };
};
