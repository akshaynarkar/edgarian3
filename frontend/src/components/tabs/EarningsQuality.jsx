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
  { label: "6Y",  value: 6 },
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
    style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 2,
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
            padding: "3px 10px",
            fontSize: 11,
            fontFamily: "Helvetica Neue, sans-serif",
            fontWeight: selected === opt.value ? 600 : 400,
            background: selected === opt.value ? "var(--text)" : "var(--bg3)",
            color: selected === opt.value ? "var(--bg)" : "var(--muted)",
            border: "0.5px solid var(--border2)",
            borderRadius: 20,
            cursor: "pointer",
          }}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

export default function EarningsQuality({
  earningsSeries,
  earningsSummary,
  debtMaturity,
  deModel,
  latestCapitalStructure,
  symbol,
  onYearsChange,
  selectedYears,
}) {
  const [localYears, setLocalYears] = useState(selectedYears || 6);

  function handleYearsChange(val) {
    setLocalYears(val);
    if (typeof onYearsChange === "function") onYearsChange(val);
  }

  return (
    <section className="grid-1">
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

      <div className="grid-2">
        <article className="card" style={{ minWidth: 0 }}>
          <h2 className="card-title">Capital Structure Snapshot</h2>
          {latestCapitalStructure ? (
            <div className="grid-1">
              <div className="kpi"><div className="kpi-label">Long-term debt</div><div className="kpi-value">{currency(latestCapitalStructure.long_term_debt)}</div></div>
              <div className="kpi"><div className="kpi-label">Total equity</div><div className="kpi-value">{currency(latestCapitalStructure.total_equity)}</div></div>
              <div className="kpi"><div className="kpi-label">Free cash flow</div><div className="kpi-value">{currency(latestCapitalStructure.free_cash_flow)}</div></div>
              <CitationLink {...latestCapitalStructure.citation} />
            </div>
          ) : (
            <div className="empty">No capital structure data available.</div>
          )}
        </article>

        <article className="card" style={{ minWidth: 0 }}>
          <h2 className="card-title">D/E Model</h2>
          <p className="card-subtitle">Three auto-computed scenarios: Base, Bull, and Bear.</p>
          {deModel.length === 0 ? (
            <div className="empty">No D/E model data available.</div>
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr><th>Scenario</th><th>Year</th><th>D/E</th><th>FCF</th><th>Refi Rate</th><th>Covenant</th><th>Citation</th></tr>
                </thead>
                <tbody>
                  {deModel.flatMap((scenario) =>
                    scenario.projections.map((p) => (
                      <tr key={`${scenario.scenario}-${p.year}`}>
                        <td>{scenario.scenario}</td>
                        <td>{p.year}</td>
                        <td>{percent((p.de_ratio || 0) * 100)}</td>
                        <td>{currency(p.fcf)}</td>
                        <td>{percent(p.refinancing_rate)}</td>
                        <td>{p.covenant_breach ? <span className="badge badge--red">Breach</span> : <span className="badge badge--green">Clear</span>}</td>
                        <td><CitationLink {...p.citation} /></td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </article>
      </div>

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
