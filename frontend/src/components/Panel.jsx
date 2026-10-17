import { formatTimestamp } from "../format.js";

// True when the data has at least one real number to draw.
function hasAnyPoints(data) {
  if (!data || !data.series) return false;
  return Object.values(data.series).some((values) => values.some((value) => value !== null));
}

// The frame shared by all six panels. It decides what to show for every state:
//   pending     -> loading placeholder
//   unavailable -> clear message (stats show "---")
//   stale       -> data is still drawn, with an amber warning
//   ok          -> normal
//
//   indicator      the object returned by the API for this panel (or undefined)
//   connectionLost true when the browser could not reach the API on its last try
//   renderStats    (summary) => stat cards;  renderChart (data) => chart
export default function Panel({ indicator, title, subtitle, connectionLost, renderStats, renderChart }) {
  const status = indicator ? indicator.status : "pending";
  const data = indicator ? indicator.data : null;
  const dataIsDrawable = hasAnyPoints(data);

  let banner = null;
  if (status === "stale") {
    banner = `Stale data: the latest refresh failed. Showing figures fetched ${formatTimestamp(indicator.fetched_at)}.`;
  } else if (connectionLost && dataIsDrawable) {
    banner = "Connection lost: showing the last data received (stale).";
  }

  let chartArea;
  if (status === "pending") {
    chartArea = <div className="panel-message loading"><span className="spinner" /> Loading data…</div>;
  } else if (status === "unavailable") {
    chartArea = (
      <div className="panel-message error">
        Data unavailable. The source could not be reached and no earlier data is stored.
      </div>
    );
  } else if (!dataIsDrawable) {
    chartArea = <div className="panel-message">No data points available for this indicator.</div>;
  } else {
    chartArea = renderChart(data);
  }

  return (
    <section className="panel" aria-label={title}>
      <h2 className="panel-title">
        {title} {subtitle && <span className="panel-subtitle">{subtitle}</span>}
      </h2>

      {banner && <div className="stale-banner" role="status">{banner}</div>}

      <div className="stat-row">{renderStats(data ? data.summary : null)}</div>

      <div className="chart-area">{chartArea}</div>

      <div className="panel-source">
        {indicator ? (
          <>
            Source:{" "}
            <a href={indicator.source.url} target="_blank" rel="noreferrer">{indicator.source.name}</a>
            {indicator.source.is_nse ? "" : " (non-NSE)"} · As of {indicator.as_of || "---"}
          </>
        ) : (
          "Source: ---"
        )}
      </div>
    </section>
  );
}
