import React, { useState } from "react";
import {
  Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import CitationLink from "../CitationLink.jsx";

const COLOR_NI   = "#97c459";
const COLOR_FCF  = "#ef9f27";
const COLOR_DEBT = "#f09595";

const YEAR_OPTIONS = [
  { label: "6Y",  value: 6  },
  { label: "10Y", value: 10 },
  { label: "15Y", value: 15 },
  { label: "MAX", value: 20 },
];

function formatB(value) {
  if (value === null || value === undefined) return "—";
  const abs = Math.abs(value);
  if (abs >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  return `$${value.toLocaleString()}`;
}

function currency(value) {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat(undefined, {
    style: "currency", currency: "USD",
    notation: "compact", maximumFractionDigits: 2,
  }).format(value);
}

function percent(value) {
  if (value === null || value === undefined) return "—";
  return `${value.toFixed(2)}%`;
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="card" style={{ padding: 12 }}>
      <div style={{ fontWeight: 600, marginBottom: 8 }}>{label}</div>
      {payload.map((item) => (
        <div key={item.dataKey} style={{ fontSize: 12, color: item.color }}>
          {item.name}: {formatB(item.value)}
        </div>
      ))}
    </div>
  );
}

function YearToggle({ selected, onChange }) {
  return (
    <div style={{ display: "flex", gap: 4 }}>
      {YEAR_OPTIONS.map((opt) => (
        <button
          key={opt.label}
          type="button"
          onClick={() => onChange(opt.value)}
          style={{
            padding: "3px 10px", fontSize: 11,
            fontFamily: "Helvetica Neue, sans-serif",
            fontWeight: selected === opt.value ? 600 : 400,
            background: selected === opt.value ? "var(--text)" : "var(--bg3)",
            color: selected === opt.value ? "var(--bg)" : "var(--muted)",
            border: "0.5px solid var(--border2)", borderRadius: 20, cursor: "pointer",
          }}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

// D/E scenario card — shows assumptions + 5-year projected D/E trend
function DeScenarioCard({ scenario }) {
  const { scenario: name, assumptions, projections } = scenario;
  const color = name === "Bull" ? "#97c459" : name === "Bear" ? "#f09595" : "#ef9f27";
  const firstDE  = projections[0]?.de_ratio;
  const lastDE   = projections[projections.length - 1]?.de_ratio;
  const direction = firstDE != null && lastDE != null
    ? lastDE < firstDE ? "↓ Declining" : lastDE > firstDE ? "↑ Rising" : "→ Flat"
    : "—";
  const hasBreach = projections.some((p) => p.covenant_breach);

  return (
    <div style={{
      border: `0.5px solid var(--border2)`,
      borderLeft: `3px solid ${color}`,
      borderRadius: 8, padding: "14px 16px",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <span style={{ fontWeight: 600, fontSize: 14 }}>{name}</span>
        {hasBreach
          ? <span className="badge badge--red">Covenant risk</span>
          : <span className="badge badge--green">No breach</span>}
      </div>

      {/* Assumptions row */}
      <div style={{ display: "flex", gap: 16, marginBottom: 12, flexWrap: "wrap" }}>
        {[
          ["FCF growth", `${assumptions.fcf_growth_pct >= 0 ? "+" : ""}${assumptions.fcf_growth_pct}% / yr`],
          ["Debt paydown", `${assumptions.paydown_ratio_pct}% of FCF`],
          ["Refi rate",   `${assumptions.refinancing_rate_pct}%`],
        ].map(([label, val]) => (
          <div key={label}>
            <div style={{ fontSize: 10, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--muted)", marginBottom: 2 }}>{label}</div>
            <div style={{ fontSize: 13, fontWeight: 500 }}>{val}</div>
          </div>
        ))}
      </div>

      {/* 5-year D/E progression */}
      <div style={{ display: "flex", gap: 8, alignItems: "flex-end", marginBottom: 8 }}>
        {projections.map((p) => {
          const de = p.de_ratio;
          const barH = de != null ? Math.min(Math.max(de * 20, 4), 48) : 4;
          return (
            <div key={p.year} style={{ textAlign: "center", flex: 1 }}>
              <div style={{ fontSize: 9, color: "var(--muted)", marginBottom: 2 }}>
                {de != null ? de.toFixed(2) : "—"}
              </div>
              <div style={{
                height: barH, background: p.covenant_breach ? "#f09595" : color,
                borderRadius: 2, opacity: 0.85,
              }} />
              <div style={{ fontSize: 9, color: "var(--muted)", marginTop: 3 }}>{p.year}</div>
            </div>
          );
        })}
      </div>

      <div style={{ fontSize: 11, color: "var(--muted)" }}>
        D/E trend: <span style={{ color, fontWeight: 600 }}>{direction}</span>
        {" · "}Start: <strong>{firstDE?.toFixed(2) ?? "—"}</strong>
        {" · "}End: <strong>{lastDE?.toFixed(2) ?? "—"}</strong>
      </div>
    </div>
  );
}

export default function EarningsQuality({
  earningsSeries, earningsSummary, debtMaturity, deModel,
  latestCapitalStructure, symbol, onYearsChange, selectedYears,
}) {
  const [localYears, setLocalYears] = useState(selectedYears || 6);

  function handleYearsChange(val) {
    setLocalYears(val);
    if (typeof onYearsChange === "function") onYearsChange(val);
  }

  return (
    <section className="grid-1">

      {/* Row 1: FCF vs NI + Debt Maturity */}
      <div className="grid-2">

        {/* FCF vs NI */}
        <article className="card" style={{ minWidth: 0 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
            <div>
              <h2 className="card-title" style={{ marginBottom: 4 }}>FCF vs Net Income</h2>
              <p className="card-subtitle">Divergence flagged when FCF materially diverges from NI.</p>
            </div>
            <YearToggle selected={localYears} onChange={handleYearsChange} />
          </div>
          {earningsSeries.length === 0 ? (
            <div className="empty">No earnings data. Run: <code>tenk_parser_multi('{symbol}', 6)</code></div>
          ) : (
            <div className="chart-wrap">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={earningsSeries} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid stroke="var(--border2)" vertical={false} />
                  <XAxis dataKey="year" stroke="var(--muted)" tick={{ fontSize: 11, fill: "var(--muted)" }} />
                  <YAxis stroke="var(--muted)" tick={{ fontSize: 11, fill: "var(--muted)" }} tickFormatter={formatB} width={68} />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="net_income" name="Net Income" fill={COLOR_NI} maxBarSize={80} />
                  <Line type="monotone" dataKey="free_cash_flow" name="Free Cash Flow"
                    stroke={COLOR_FCF} strokeWidth={2}
                    dot={{ r: 4, fill: COLOR_FCF, strokeWidth: 0 }} activeDot={{ r: 6 }} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}
          <div className="data-list">
            {earningsSeries.map((row) => (
              <div className="data-list-row" key={row.year}>
                <div>
                  <strong>{row.year}</strong>
                  <div className="meta-row">
                    <span>{currency(row.net_income)} NI</span>
                    <span>{currency(row.free_cash_flow)} FCF</span>
                    {row.divergence
                      ? <span className={`badge ${row.divergence_direction === "fcf_below_ni" ? "badge--red" : "badge--amber"}`}>Divergence</span>
                      : <span className="badge badge--green">Aligned</span>}
                  </div>
                </div>
                <CitationLink {...row.citation} />
              </div>
            ))}
          </div>
        </article>

        {/* Debt Maturity */}
        <article className="card" style={{ minWidth: 0 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
            <div>
              <h2 className="card-title" style={{ marginBottom: 4 }}>Debt Maturity Schedule</h2>
              <p className="card-subtitle">Principal balances by maturity year.</p>
            </div>
            <YearToggle selected={localYears} onChange={handleYearsChange} />
          </div>
          {debtMaturity.length === 0 ? (
            <div className="empty">No debt schedule data available.</div>
          ) : (
            <div className="chart-wrap">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={debtMaturity} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid stroke="var(--border2)" vertical={false} />
                  <XAxis dataKey="maturity_year" stroke="var(--muted)" tick={{ fontSize: 11, fill: "var(--muted)" }} />
                  <YAxis stroke="var(--muted)" tick={{ fontSize: 11, fill: "var(--muted)" }} tickFormatter={formatB} width={68} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="amount" name="Debt Amount" fill={COLOR_DEBT} maxBarSize={80} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
          <div className="data-list">
            {debtMaturity.map((row) => (
              <div className="data-list-row" key={row.maturity_year}>
                <div>
                  <strong>{row.maturity_year}</strong>
                  <div className="meta-row">
                    <span>{currency(row.amount)}</span>
                    <span>{row.instruments?.join(", ") || "Debt instruments"}</span>
                  </div>
                </div>
                <CitationLink {...row.citations?.[0]} />
              </div>
            ))}
          </div>
        </article>

      </div>

      {/* Row 2: Capital Structure + D/E Scenarios */}
      <div className="grid-2">

        <article className="card" style={{ minWidth: 0 }}>
          <h2 className="card-title">Capital Structure</h2>
          {latestCapitalStructure ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 8 }}>
              {[
                ["Long-term debt",  latestCapitalStructure.long_term_debt],
                ["Total equity",    latestCapitalStructure.total_equity],
                ["Free cash flow",  latestCapitalStructure.free_cash_flow],
              ].map(([label, val]) => (
                <div key={label} style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                  <span style={{ fontSize: 12, color: "var(--muted)" }}>{label}</span>
                  <span style={{ fontSize: 15, fontWeight: 600 }}>{currency(val)}</span>
                </div>
              ))}
              <CitationLink {...latestCapitalStructure.citation} />
            </div>
          ) : (
            <div className="empty">No capital structure data available.</div>
          )}
        </article>

        <article className="card" style={{ minWidth: 0 }}>
          <h2 className="card-title" style={{ marginBottom: 4 }}>D/E Scenario Model</h2>
          <p className="card-subtitle" style={{ marginBottom: 12 }}>
            5-year projected debt/equity under Base · Bull · Bear assumptions. Auto-computed from latest filing.
          </p>
          {deModel.length === 0 ? (
            <div className="empty">No D/E model data available.</div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {deModel.map((s) => <DeScenarioCard key={s.scenario} scenario={s} />)}
            </div>
          )}
        </article>

      </div>

      {/* Row 3: Latest filing summary strip */}
      {earningsSummary?.latest_period && (
        <article className="card">
          <div className="eyebrow">Latest filing summary</div>
          <div className="meta-row" style={{ marginTop: 8 }}>
            <span>Period: {earningsSummary.latest_period}</span>
            <span>NI: {currency(earningsSummary.latest_net_income)}</span>
            <span>FCF: {currency(earningsSummary.latest_free_cash_flow)}</span>
            <span>Divergence: {earningsSummary.has_recent_divergence
              ? <span className="badge badge--red">Yes</span>
              : <span className="badge badge--green">No</span>}
            </span>
          </div>
        </article>
      )}

    </section>
  );
}
