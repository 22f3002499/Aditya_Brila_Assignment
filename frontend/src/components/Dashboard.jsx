import { useEffect, useState } from "react";
import { ApiError, fetchDashboard, fetchTicker } from "../api.js";
import { formatNumber } from "../format.js";
import { GradientDefinitions, DebtChart, ExpenditureChart, GdpChart, GstChart, InflationChart, TradeChart } from "./Charts.jsx";
import { IndiaFlag, PictureIcon, UsFlag, WorldGlobe } from "./Icons.jsx";
import Panel from "./Panel.jsx";
import StatCard from "./StatCard.jsx";
import Ticker from "./Ticker.jsx";

// How often the browser asks the API for fresh data (the API only reads its own database).
const TICKER_POLL_MS = 30 * 1000;
const DASHBOARD_POLL_MS = 5 * 60 * 1000;

// Loads the data, keeps it fresh, and tells the parent when the user is signed out.
function useDashboardData(token, onSignedOut) {
  const [indicators, setIndicators] = useState(null); // null until the first response
  const [connectionLost, setConnectionLost] = useState(false);

  useEffect(() => {
    let isActive = true; // becomes false when the component is removed

    function handleFailure(error) {
      if (!isActive) return;
      if (error instanceof ApiError && error.status === 401) {
        onSignedOut("Your session has expired. Please sign in again.");
      } else {
        setConnectionLost(true); // keep showing the old data, labelled stale
      }
    }

    async function loadEverything() {
      try {
        const response = await fetchDashboard(token);
        if (!isActive) return;
        setIndicators(response.indicators);
        setConnectionLost(false);
      } catch (error) {
        handleFailure(error);
      }
    }

    async function loadTickerOnly() {
      try {
        const tickerIndicator = await fetchTicker(token);
        if (!isActive) return;
        setIndicators((current) => (current ? { ...current, ticker: tickerIndicator } : current));
        setConnectionLost(false);
      } catch (error) {
        handleFailure(error);
      }
    }

    loadEverything();
    const tickerTimer = setInterval(loadTickerOnly, TICKER_POLL_MS);
    const dashboardTimer = setInterval(loadEverything, DASHBOARD_POLL_MS);
    return () => {
      isActive = false;
      clearInterval(tickerTimer);
      clearInterval(dashboardTimer);
    };
  }, [token, onSignedOut]);

  return { indicators, connectionLost };
}

export default function Dashboard({ token, onSignOut, onSignedOut }) {
  const { indicators, connectionLost } = useDashboardData(token, onSignedOut);
  const [yearCount, setYearCount] = useState(5); // the 5Y / 10Y selector

  // Convenience: get one indicator (undefined while still loading).
  const get = (key) => (indicators ? indicators[key] : undefined);

  // Reads one entry of a panel's summary safely: missing -> an empty object.
  const pick = (summary, name) => (summary && summary[name]) || {};

  return (
    <div className="dashboard">
      <GradientDefinitions />
      <header className="dashboard-header">
        <h1 className="dashboard-title">ECONOMIC INDICATOR</h1>
        <div className="header-controls">
          <div className="range-toggle" role="group" aria-label="Years shown">
            {[5, 10].map((count) => (
              <button key={count} type="button" className={yearCount === count ? "active" : ""}
                      onClick={() => setYearCount(count)}>
                {count}Y
              </button>
            ))}
          </div>
          <button type="button" className="sign-out" onClick={onSignOut}>Sign out</button>
        </div>
      </header>

      <Ticker indicator={get("ticker")} connectionLost={connectionLost} />

      {connectionLost && !indicators && (
        <div className="page-error" role="alert">Cannot reach the server. Retrying automatically…</div>
      )}

      <main className="panel-grid">
        {/* 1. GDP growth */}
        <Panel indicator={get("gdp")} title="GDP Growth - India vs World" subtitle="(YOY%)" connectionLost={connectionLost}
          renderStats={(summary) => (
            <>
              <StatCard icon={<IndiaFlag />} label="India" value={formatNumber(pick(summary, "india").value, { suffix: "%" })}
                        change={pick(summary, "india").change} changeUnit="pp" />
              <StatCard icon={<WorldGlobe />} label="World" value={formatNumber(pick(summary, "world").value, { suffix: "%" })}
                        change={pick(summary, "world").change} changeUnit="pp" />
            </>
          )}
          renderChart={(data) => <GdpChart data={data} yearCount={yearCount} />} />

        {/* 2. Debt to GDP */}
        <Panel indicator={get("debt")} title="Debt to GDP Ratio" subtitle="(IND)" connectionLost={connectionLost}
          renderStats={(summary) => (
            <>
              <StatCard icon={<IndiaFlag />} label={`India (${pick(summary, "india").period || "---"})`}
                        value={formatNumber(pick(summary, "india").value, { suffix: "%" })}
                        change={pick(summary, "india").change} changeUnit="pp" />
              <StatCard icon={<UsFlag />} label="United States"
                        value={formatNumber(pick(summary, "usa").value, { suffix: "%" })}
                        change={pick(summary, "usa").change} changeUnit="pp" />
            </>
          )}
          renderChart={(data) => <DebtChart data={data} yearCount={yearCount} />} />

        {/* 3. Imports, exports and trade balance */}
        <Panel indicator={get("trade")} title="Imports, Exports & Trade Balance" connectionLost={connectionLost}
          renderStats={(summary) => (
            <>
              <StatCard icon={<PictureIcon kind="trade" />} label="Exports"
                        value={formatNumber(pick(summary, "exports").value, { decimals: 1, prefix: "$", suffix: " B" })}
                        change={pick(summary, "exports").change} changeUnit="%" />
              <StatCard icon={<PictureIcon kind="trade" />} label="Imports"
                        value={formatNumber(pick(summary, "imports").value, { decimals: 1, prefix: "$", suffix: " B" })}
                        change={pick(summary, "imports").change} changeUnit="%" />
            </>
          )}
          renderChart={(data) => <TradeChart data={data} yearCount={yearCount} />} />

        {/* 4. GST collection */}
        <Panel indicator={get("gst")} title="GST Tax Collection" subtitle="(YOY%)" connectionLost={connectionLost}
          renderStats={(summary) => (
            <>
              <StatCard icon={<PictureIcon kind="coin" />} label="GST Collections (₹ lakh cr)"
                        value={formatNumber(pick(summary, "collections").value)}
                        change={pick(summary, "collections").change} changeUnit="%" />
              <StatCard icon={<PictureIcon kind="chart" />} label="Monthly Average (₹ lakh cr)"
                        value={formatNumber(pick(summary, "monthly_average").value)}
                        change={pick(summary, "monthly_average").change} changeUnit="%" />
            </>
          )}
          renderChart={(data) => <GstChart data={data} yearCount={yearCount} />} />

        {/* 5. Inflation */}
        <Panel indicator={get("inflation")} title="Inflation" subtitle="(IND)" connectionLost={connectionLost}
          renderStats={(summary) => (
            <>
              <StatCard icon={<PictureIcon kind="chart" />} label="Inflation Rate"
                        value={formatNumber(pick(summary, "rate").value, { suffix: "%" })}
                        change={pick(summary, "rate").change} changeUnit="pp" />
              <StatCard icon={<PictureIcon kind="target" />} label="RBI Target"
                        value={formatNumber(pick(summary, "target").value, { decimals: 0, suffix: "%" })}
                        change={null} changeUnit="pp" />
            </>
          )}
          renderChart={(data) => <InflationChart data={data} yearCount={yearCount} />} />

        {/* 6. Government expenditure */}
        <Panel indicator={get("expenditure")} title="Government Expenditure" connectionLost={connectionLost}
          renderStats={(summary) => (
            <>
              <StatCard icon={<PictureIcon kind="bank" />} label="Total Expenditure (₹ lakh cr)"
                        value={formatNumber(pick(summary, "total").value)}
                        change={pick(summary, "total").change} changeUnit="%" />
              <StatCard icon={<PictureIcon kind="bank" />} label="Capital Expenditure (₹ lakh cr)"
                        value={formatNumber(pick(summary, "capital").value)}
                        change={pick(summary, "capital").change} changeUnit="%" />
            </>
          )}
          renderChart={(data) => <ExpenditureChart data={data} yearCount={yearCount} />} />
      </main>
    </div>
  );
}
