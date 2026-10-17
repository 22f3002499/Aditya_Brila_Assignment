import { MISSING, formatNumber, isMissing } from "../format.js";

// A small summary card: icon, label, big value and the change since the previous period.
//   value  - already formatted text (use formatNumber so missing data shows "---")
//   change - number or null, changeUnit - "pp" (percentage points) or "%"
export default function StatCard({ icon, label, value, change, changeUnit }) {
  const changeIsMissing = isMissing(change);
  const isRise = !changeIsMissing && change >= 0;

  let changeClass = "change-pill missing";
  let changeText = MISSING;
  if (!changeIsMissing) {
    changeClass = isRise ? "change-pill up" : "change-pill down";
    changeText = `${isRise ? "▲" : "▼"} ${formatNumber(Math.abs(change), { decimals: 2 })}${changeUnit}`;
  }

  return (
    <div className="stat-card">
      <div className="stat-text">
        <div className="stat-label">{label}</div>
        <div className="stat-value">{value}</div>
        <span className={changeClass}>{changeText}</span>
      </div>
      <div className="stat-icon">{icon}</div>
    </div>
  );
}
