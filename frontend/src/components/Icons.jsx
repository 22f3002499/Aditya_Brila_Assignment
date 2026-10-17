// Small decorative icons drawn as inline SVG (no image files needed).

export function IndiaFlag() {
  return (
    <svg viewBox="0 0 32 32" className="flag" aria-label="India">
      <clipPath id="flag-circle-in"><circle cx="16" cy="16" r="15" /></clipPath>
      <g clipPath="url(#flag-circle-in)">
        <rect width="32" height="11" y="0" fill="#ff9933" />
        <rect width="32" height="10" y="11" fill="#ffffff" />
        <rect width="32" height="11" y="21" fill="#138808" />
        <circle cx="16" cy="16" r="3.5" fill="none" stroke="#000080" strokeWidth="1" />
      </g>
    </svg>
  );
}

export function UsFlag() {
  return (
    <svg viewBox="0 0 32 32" className="flag" aria-label="United States">
      <clipPath id="flag-circle-us"><circle cx="16" cy="16" r="15" /></clipPath>
      <g clipPath="url(#flag-circle-us)">
        <rect width="32" height="32" fill="#ffffff" />
        {[0, 1, 2, 3, 4, 5, 6].map((stripe) => (
          <rect key={stripe} y={stripe * 4.6} width="32" height="2.3" fill="#c8323c" />
        ))}
        <rect width="15" height="16" fill="#26357a" />
      </g>
    </svg>
  );
}

export function WorldGlobe() {
  return (
    <svg viewBox="0 0 32 32" className="flag" aria-label="World">
      <circle cx="16" cy="16" r="15" fill="#1b5fa8" />
      <path d="M8 11c3-3 6-2 7 0s-1 4-3 4-3 2-1 4-3 3-4 1-1-6 1-9z" fill="#4fae5b" />
      <path d="M19 8c3 0 6 2 6 5s-3 3-4 5-1 5-3 4 0-6-1-8 0-6 2-6z" fill="#4fae5b" />
    </svg>
  );
}

// One generic pictogram per panel theme, drawn with simple shapes.
export function PictureIcon({ kind }) {
  const strokeColor = "#6fd0ff";
  const fillColor = "#f5a623";
  const shapes = {
    chart: (
      <>
        <rect x="6" y="22" width="6" height="12" fill={strokeColor} />
        <rect x="16" y="14" width="6" height="20" fill={fillColor} />
        <rect x="26" y="6" width="6" height="28" fill={strokeColor} />
      </>
    ),
    trade: (
      <>
        <rect x="6" y="16" width="26" height="16" fill={fillColor} />
        <path d="M6 16l6-8h14l6 8z" fill={strokeColor} />
      </>
    ),
    coin: (
      <>
        <circle cx="19" cy="20" r="13" fill={fillColor} />
        <text x="19" y="26" textAnchor="middle" fontSize="16" fontWeight="700" fill="#1a1a1a">₹</text>
      </>
    ),
    target: (
      <>
        <circle cx="19" cy="20" r="14" fill="none" stroke={strokeColor} strokeWidth="3" />
        <circle cx="19" cy="20" r="8" fill="none" stroke={fillColor} strokeWidth="3" />
        <circle cx="19" cy="20" r="2.5" fill={strokeColor} />
      </>
    ),
    bank: (
      <>
        <path d="M4 14L19 5l15 9z" fill={fillColor} />
        <rect x="8" y="16" width="4" height="14" fill={strokeColor} />
        <rect x="17" y="16" width="4" height="14" fill={strokeColor} />
        <rect x="26" y="16" width="4" height="14" fill={strokeColor} />
        <rect x="5" y="31" width="28" height="4" fill={fillColor} />
      </>
    ),
  };
  return (
    <svg viewBox="0 0 38 40" className="picture-icon" aria-hidden="true">
      {shapes[kind]}
    </svg>
  );
}
