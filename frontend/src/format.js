// Small formatting helpers. A missing value is ALWAYS shown as "---".

export const MISSING = "---";

export function isMissing(value) {
  return value === null || value === undefined || Number.isNaN(value);
}

// formatNumber(4.826, { decimals: 2, suffix: "%" }) -> "4.83%"
export function formatNumber(value, { decimals = 2, prefix = "", suffix = "" } = {}) {
  if (isMissing(value)) return MISSING;
  return `${prefix}${value.toFixed(decimals)}${suffix}`;
}

// Index levels such as 73,158.24 use thousands separators.
export function formatIndexLevel(value) {
  if (isMissing(value)) return MISSING;
  return value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Shows "5 Jan, 14:30" style text for an ISO timestamp.
export function formatTimestamp(isoText) {
  if (!isoText) return MISSING;
  const date = new Date(isoText);
  if (Number.isNaN(date.getTime())) return MISSING;
  return date.toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}
