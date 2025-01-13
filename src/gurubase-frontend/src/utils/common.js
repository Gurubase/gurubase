export function nFormatter(num, digits) {
  const lookup = [
    { value: 1, symbol: "" },
    { value: 1e3, symbol: "K" },
    { value: 1e6, symbol: "M" },
    { value: 1e9, symbol: "G" },
    { value: 1e12, symbol: "T" },
    { value: 1e15, symbol: "P" },
    { value: 1e18, symbol: "E" }
  ];
  const rx = /\.0+$|(\.[0-9]*[1-9])0+$/;
  var item = lookup
    .slice()
    .reverse()
    .find(function (item) {
      return num >= item.value;
    });

  return item
    ? (num / item.value).toFixed(digits).replace(rx, "$1") + item.symbol
    : "0";
}

export const toCapitalize = (str) => {
  // Check if str exists and is a string
  if (typeof str !== "string" || str.length === 0) {
    return "";
  }

  return str.charAt(0).toUpperCase() + str.slice(1);
};

const createFingerprint = async () => {
  const { ClientJS } = (await import("clientjs")).default;
  const client = new ClientJS();
  const fingerprint = client.getFingerprint();

  return fingerprint;
};

export const getFingerPrint = async () => {
  //check if localstorage exists
  if (typeof window === "undefined") {
    return null;
  }
  let fingerprint = localStorage.getItem("fingerprint");

  if (fingerprint) {
    return fingerprint;
  } else {
    fingerprint = await createFingerprint();
    localStorage.setItem("fingerprint", fingerprint);

    return fingerprint;
  }
};

export const isValidUrl = (url) => {
  if (!url || url.trim() === "") return false;

  try {
    const urlObj = new URL(url.trim());
    const hostname = urlObj.hostname;

    // Check if hostname has at least one dot and consists of valid characters
    return (
      hostname.includes(".") &&
      // Allow letters, numbers, dots, and hyphens, but dots can't be consecutive
      /^(?!-)[A-Za-z0-9-]+([-.][A-Za-z0-9-]+)*\.[A-Za-z]{2,}$/.test(hostname)
    );
  } catch (e) {
    return false;
  }
};

export const getNormalizedDomain = (url) => {
  try {
    const hostname = new URL(url).hostname;

    // Remove www. prefix if it exists
    return hostname.replace(/^www\./, "");
  } catch (error) {
    return null;
  }
};

export const determineInitialTab = (domains) => {
  const statusCounts = domains.reduce((acc, domain) => {
    const status =
      domain.status === "NOT_PROCESSED"
        ? "not_processed"
        : domain.status?.toLowerCase() === "fail"
          ? "failed"
          : "success";

    acc[status] = (acc[status] || 0) + 1;

    return acc;
  }, {});

  // Find the status with the highest count
  const [defaultTab] = Object.entries(statusCounts).sort(
    ([, a], [, b]) => b - a
  )[0] || ["success"];

  return defaultTab;
};
