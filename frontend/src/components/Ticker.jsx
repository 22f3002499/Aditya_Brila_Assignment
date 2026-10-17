import { MISSING, formatIndexLevel, formatNumber, isMissing } from "../format.js";

// The scrolling market ticker under the page title.
export default function Ticker({ indicator, connectionLost }) {
  const status = indicator ? indicator.status : "pending";
  const items = indicator && indicator.data ? indicator.data.items : [];
  const isStale = status === "stale" || (connectionLost && items.length > 0);
  const isLive = status === "ok" && !connectionLost;

  let badgeText = "LIVE";
  let badgeClass = "live-badge";
  if (isStale) {
    badgeText = "STALE";
    badgeClass = "live-badge stale";
  } else if (!isLive) {
    badgeText = status === "pending" ? "LOADING" : "OFFLINE";
    badgeClass = "live-badge offline";
  }

  // The list is shown twice so the scrolling loop has no visible gap.
  const scrollingItems = [...items, ...items];

  return (
    <div className="ticker-wrapper">
      <div className="ticker-bar">
        <span className={badgeClass}>
          <span className="live-dot" /> {badgeText}
        </span>

        <div className="ticker-window">
          {items.length === 0 ? (
            <span className="ticker-empty">
              {status === "pending" ? "Loading market data…" : `Market data unavailable ${MISSING}`}
            </span>
          ) : (
            <div className="ticker-track" style={{ animationDuration: `${items.length * 6}s` }}>
              {scrollingItems.map((item, position) => {
                const isUp = !isMissing(item.percent_change) && item.percent_change >= 0;
                return (
                  <span className="ticker-item" key={`${item.name}-${position}`}>
                    <span className="ticker-name">{item.name}</span>
                    <span className="ticker-value">{formatIndexLevel(item.last)}</span>
                    <span className={isUp ? "ticker-change up" : "ticker-change down"}>
                      {isMissing(item.change) ? MISSING : formatNumber(item.change, { decimals: 2 })}{" "}
                      ({isUp ? "+" : ""}{formatNumber(item.percent_change, { decimals: 2, suffix: "%" })})
                    </span>
                  </span>
                );
              })}
            </div>
          )}
        </div>
      </div>

      <div className="ticker-source">
        Source:{" "}
        <a href={indicator ? indicator.source.url : "https://www.nseindia.com"} target="_blank" rel="noreferrer">
          NSE India
        </a>{" "}
        · As of {indicator && indicator.as_of ? indicator.as_of : MISSING}
        {isStale ? " · stale" : ""}
      </div>
    </div>
  );
}
