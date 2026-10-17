import { useState } from "react";
import {
  Area, Bar, CartesianGrid, ComposedChart, LabelList, Line, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { MISSING, isMissing } from "../format.js";

// ------------------------------------------------------------------ shared pieces

const COLORS = {
  blue: "#1c9be0", orange: "#f5a623", green: "#34d17f", yellow: "#f7d046", cyan: "#25c7e6",
  axisText: "#9fb3c8", grid: "rgba(120, 160, 210, 0.15)",
};

// Turns the API's {years, series} shape into one row per year, the shape Recharts expects:
//   [{ label: "2023", india: 8.1, world: 3.0 }, ...]
// Only the newest `yearCount` years are kept (the 5Y / 10Y selector).
function buildRows(data, yearCount, labelPrefix = "") {
  const firstPosition = Math.max(0, data.years.length - yearCount);
  const rows = [];
  for (let position = firstPosition; position < data.years.length; position++) {
    const row = { label: `${labelPrefix}${data.years[position]}` };
    for (const seriesName of Object.keys(data.series)) {
      row[seriesName] = data.series[seriesName][position]; // may be null (missing)
    }
    rows.push(row);
  }
  return rows;
}

// Remembers which series the user switched off by clicking the legend.
function useHiddenSeries() {
  const [hiddenNames, setHiddenNames] = useState([]);
  function toggle(seriesName) {
    setHiddenNames((current) =>
      current.includes(seriesName) ? current.filter((name) => name !== seriesName) : [...current, seriesName]
    );
  }
  return { isHidden: (seriesName) => hiddenNames.includes(seriesName), toggle };
}

// Clickable legend: each entry shows or hides its series.
function Legend({ items, hiddenSeries }) {
  return (
    <div className="legend">
      {items.map((item) => (
        <button
          key={item.name}
          type="button"
          className={hiddenSeries.isHidden(item.name) ? "legend-item off" : "legend-item"}
          onClick={() => hiddenSeries.toggle(item.name)}
          aria-pressed={!hiddenSeries.isHidden(item.name)}
        >
          <span className={`legend-swatch ${item.shape || "box"}`} style={{ background: item.color }} />
          {item.label}
        </button>
      ))}
    </div>
  );
}

function ChartTooltip({ active, payload, label, unit, labels }) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="chart-tooltip">
      <div className="tooltip-title">{label}</div>
      {payload.map((entry) => (
        <div key={entry.dataKey} style={{ color: entry.color || entry.stroke }}>
          {labels[entry.dataKey] || entry.dataKey}:{" "}
          {isMissing(entry.value) ? MISSING : `${entry.value}${unit}`}
        </div>
      ))}
    </div>
  );
}

// Shared look of the axes and grid.
const axisProps = { tick: { fill: COLORS.axisText, fontSize: 11 }, axisLine: false, tickLine: false };

// Gradient colours used by the bars and areas. Recharts does not draw <defs> placed
// inside a chart, so they live once in a hidden SVG on the page and charts refer to
// them by id (fill="url(#grad-blue)").
export function GradientDefinitions() {
  return (
    <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden="true">
      <defs>
        <linearGradient id="grad-blue" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#3cc4ff" /><stop offset="100%" stopColor="#0b4f86" />
        </linearGradient>
        <linearGradient id="grad-orange" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#ffc15a" /><stop offset="100%" stopColor="#b8660a" />
        </linearGradient>
        <linearGradient id="grad-area" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#25c7e6" stopOpacity="0.55" /><stop offset="100%" stopColor="#25c7e6" stopOpacity="0.02" />
        </linearGradient>
      </defs>
    </svg>
  );
}

// A bar label shows the value with one decimal, nothing when the value is missing.
const barLabelProps = { fill: "#e8f1fa", fontSize: 10, formatter: (value) => (isMissing(value) ? "" : value.toFixed(1)) };

function ChartBox({ children }) {
  return (
    <div className="chart-box">
      <ResponsiveContainer width="100%" height="100%">{children}</ResponsiveContainer>
    </div>
  );
}

const chartMargin = { top: 18, right: 8, left: -12, bottom: 0 };

// ------------------------------------------------------------------ the six charts

// 1. GDP growth: India vs World (grouped bars, % year on year)
export function GdpChart({ data, yearCount }) {
  const hidden = useHiddenSeries();
  const rows = buildRows(data, yearCount);
  return (
    <>
      <Legend hiddenSeries={hidden} items={[
        { name: "india", label: "India", color: COLORS.blue },
        { name: "world", label: "World", color: COLORS.orange },
      ]} />
      <ChartBox>
        <ComposedChart data={rows} margin={chartMargin}>
          <CartesianGrid stroke={COLORS.grid} vertical={false} />
          <XAxis dataKey="label" {...axisProps} />
          <YAxis {...axisProps} tickFormatter={(value) => `${value}%`} />
          <Tooltip content={<ChartTooltip unit="%" labels={{ india: "India", world: "World" }} />} cursor={{ fill: "rgba(255,255,255,0.05)" }} />
          {!hidden.isHidden("india") && (
            <Bar dataKey="india" fill="url(#grad-blue)" radius={[3, 3, 0, 0]} maxBarSize={22}>
              <LabelList dataKey="india" position="top" {...barLabelProps} />
            </Bar>
          )}
          {!hidden.isHidden("world") && (
            <Bar dataKey="world" fill="url(#grad-orange)" radius={[3, 3, 0, 0]} maxBarSize={22}>
              <LabelList dataKey="world" position="top" {...barLabelProps} />
            </Bar>
          )}
        </ComposedChart>
      </ChartBox>
    </>
  );
}

// 2. Debt to GDP: India (area) compared with the United States (line)
export function DebtChart({ data, yearCount }) {
  const hidden = useHiddenSeries();
  const rows = buildRows(data, yearCount);
  return (
    <>
      <Legend hiddenSeries={hidden} items={[
        { name: "india", label: "India", color: COLORS.cyan },
        { name: "usa", label: "United States", color: COLORS.orange, shape: "line" },
      ]} />
      <ChartBox>
        <ComposedChart data={rows} margin={chartMargin}>
          <CartesianGrid stroke={COLORS.grid} vertical={false} />
          <XAxis dataKey="label" {...axisProps} />
          <YAxis {...axisProps} tickFormatter={(value) => `${value}%`} domain={[0, "auto"]} />
          <Tooltip content={<ChartTooltip unit="%" labels={{ india: "India", usa: "United States" }} />} />
          {!hidden.isHidden("india") && (
            <Area dataKey="india" type="monotone" stroke={COLORS.cyan} strokeWidth={2} fill="url(#grad-area)" connectNulls={false} dot={{ r: 3, fill: COLORS.cyan }} />
          )}
          {!hidden.isHidden("usa") && (
            <Line dataKey="usa" type="monotone" stroke={COLORS.orange} strokeWidth={2} dot={{ r: 3 }} connectNulls={false} />
          )}
        </ComposedChart>
      </ChartBox>
    </>
  );
}

// 3. Imports, exports (bars, US$ billion) and trade balance (line)
export function TradeChart({ data, yearCount }) {
  const hidden = useHiddenSeries();
  const rows = buildRows(data, yearCount);
  return (
    <>
      <Legend hiddenSeries={hidden} items={[
        { name: "imports", label: "Imports", color: COLORS.blue },
        { name: "exports", label: "Exports", color: COLORS.orange },
        { name: "balance", label: "Trade Balance", color: COLORS.green, shape: "line" },
      ]} />
      <ChartBox>
        <ComposedChart data={rows} margin={chartMargin}>
          <CartesianGrid stroke={COLORS.grid} vertical={false} />
          <XAxis dataKey="label" {...axisProps} />
          <YAxis {...axisProps} tickFormatter={(value) => `$${value}B`} />
          <Tooltip content={<ChartTooltip unit=" B" labels={{ imports: "Imports", exports: "Exports", balance: "Trade balance" }} />} />
          <ReferenceLine y={0} stroke={COLORS.axisText} strokeOpacity={0.4} />
          {!hidden.isHidden("imports") && (
            <Bar dataKey="imports" fill="url(#grad-blue)" radius={[3, 3, 0, 0]} maxBarSize={22} />
          )}
          {!hidden.isHidden("exports") && (
            <Bar dataKey="exports" fill="url(#grad-orange)" radius={[3, 3, 0, 0]} maxBarSize={22} />
          )}
          {!hidden.isHidden("balance") && (
            <Line dataKey="balance" type="monotone" stroke={COLORS.green} strokeWidth={2} dot={{ r: 3, fill: COLORS.green }} connectNulls={false}>
              <LabelList dataKey="balance" position="bottom" {...barLabelProps} />
            </Line>
          )}
        </ComposedChart>
      </ChartBox>
    </>
  );
}

// 4. GST collection (bars, Rs lakh crore) and the monthly average (line, right-hand axis)
export function GstChart({ data, yearCount }) {
  const hidden = useHiddenSeries();
  const rows = buildRows(data, yearCount, "FY");
  return (
    <>
      <Legend hiddenSeries={hidden} items={[
        { name: "collections", label: "Collections (₹ lakh crore)", color: COLORS.blue },
        { name: "monthly_average", label: "Monthly average", color: COLORS.yellow, shape: "line" },
      ]} />
      <ChartBox>
        <ComposedChart data={rows} margin={{ ...chartMargin, right: -4 }}>
          <CartesianGrid stroke={COLORS.grid} vertical={false} />
          <XAxis dataKey="label" {...axisProps} />
          <YAxis yAxisId="left" {...axisProps} />
          <YAxis yAxisId="right" orientation="right" {...axisProps} domain={[0, "auto"]} />
          <Tooltip content={<ChartTooltip unit=" lakh cr" labels={{ collections: "Collections", monthly_average: "Monthly average" }} />} />
          {!hidden.isHidden("collections") && (
            <Bar yAxisId="left" dataKey="collections" fill="url(#grad-blue)" radius={[3, 3, 0, 0]} maxBarSize={26}>
              <LabelList dataKey="collections" position="top" {...barLabelProps} />
            </Bar>
          )}
          {!hidden.isHidden("monthly_average") && (
            <Line yAxisId="right" dataKey="monthly_average" type="monotone" stroke={COLORS.yellow} strokeWidth={2} dot={{ r: 3, fill: COLORS.yellow }} connectNulls={false} />
          )}
        </ComposedChart>
      </ChartBox>
    </>
  );
}

// 5. Inflation: India's CPI inflation (line) against the RBI target (dashed line)
export function InflationChart({ data, yearCount }) {
  const hidden = useHiddenSeries();
  const rows = buildRows(data, yearCount);
  return (
    <>
      <Legend hiddenSeries={hidden} items={[
        { name: "india", label: "Inflation (CPI)", color: COLORS.cyan, shape: "line" },
        { name: "target", label: `RBI target (${data.target}%)`, color: COLORS.orange, shape: "line" },
      ]} />
      <ChartBox>
        <ComposedChart data={rows} margin={chartMargin}>
          <CartesianGrid stroke={COLORS.grid} vertical={false} />
          <XAxis dataKey="label" {...axisProps} />
          <YAxis {...axisProps} tickFormatter={(value) => `${value}%`} domain={[0, "auto"]} />
          <Tooltip content={<ChartTooltip unit="%" labels={{ india: "Inflation" }} />} />
          {!hidden.isHidden("target") && (
            <ReferenceLine y={data.target} stroke={COLORS.orange} strokeDasharray="6 4" />
          )}
          {!hidden.isHidden("india") && (
            <Area dataKey="india" type="monotone" stroke={COLORS.cyan} strokeWidth={2} fill="url(#grad-area)" dot={{ r: 3, fill: COLORS.cyan }} connectNulls={false}>
              <LabelList dataKey="india" position="top" {...barLabelProps} />
            </Area>
          )}
        </ComposedChart>
      </ChartBox>
    </>
  );
}

// 6. Government expenditure: revenue + capital stacked (Rs lakh crore)
export function ExpenditureChart({ data, yearCount }) {
  const hidden = useHiddenSeries();
  const rows = buildRows(data, yearCount, "FY");
  return (
    <>
      <Legend hiddenSeries={hidden} items={[
        { name: "revenue", label: "Revenue Expenditure", color: COLORS.blue },
        { name: "capital", label: "Capital Expenditure", color: COLORS.orange },
      ]} />
      <ChartBox>
        <ComposedChart data={rows} margin={chartMargin}>
          <CartesianGrid stroke={COLORS.grid} vertical={false} />
          <XAxis dataKey="label" {...axisProps} />
          <YAxis {...axisProps} />
          <Tooltip content={<ChartTooltip unit=" lakh cr" labels={{ revenue: "Revenue", capital: "Capital" }} />} cursor={{ fill: "rgba(255,255,255,0.05)" }} />
          {!hidden.isHidden("capital") && (
            <Bar dataKey="capital" stackId="spend" fill="url(#grad-orange)" maxBarSize={34}>
              <LabelList dataKey="capital" position="center" {...barLabelProps} />
            </Bar>
          )}
          {!hidden.isHidden("revenue") && (
            <Bar dataKey="revenue" stackId="spend" fill="url(#grad-blue)" radius={[3, 3, 0, 0]} maxBarSize={34}>
              <LabelList dataKey="revenue" position="center" {...barLabelProps} />
            </Bar>
          )}
        </ComposedChart>
      </ChartBox>
    </>
  );
}
