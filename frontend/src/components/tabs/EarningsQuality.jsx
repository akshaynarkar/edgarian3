import React from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import CitationLink from "../CitationLink.jsx";

function currency(value) {
  if (value === null || value === undefined) {
    return "—";
  }
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
    notation: "compact",
    maximumFractionDigits: 2,
  }).format(value);
}

function percent(value) {
  if (value === null || value === undefined) {
    return "—";
  }
  return `${value.toFixed(2)}%`;
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) {
    return null;
  }

  return (
    <div className="card" style={{ padding: 12 }}>
      <div style={{ fontWeight: 600, marginBottom: 8 }}>{label}</div>
      {payload.map((item) => (
        <div key={item.dataKey} style={{ fontSize: 12, color: "var(--muted)" }}>
          {item.name}: {currency(item.value)}
        </div>
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
}) {
  return (
    <section className="grid-1">
      <div className="grid-2">
        <article className="card">
          <h2 className="card-title">FCF vs Net Income</h2>
          <p className="card-subtitle">
            Multi-year comparison. Divergence is flagged when free cash flow materially
            diverges from net income.
          </p>

          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={earningsSeries}>
                <CartesianGrid stroke="var(--border2)" vertical={false} />
                <XAxis dataKey="year" stroke="var(--muted)" />
                <YAxis stroke="var(--muted)" />
                <Tooltip content={<CustomTooltip />} />
                <Legend />
                <Bar dataKey="net_income" name="Net Income" fill="var(--accent)" />
                <Line
                  type="monotone"
                  dataKey="free_cash_flow"
                  name="Free Cash Flow"
                  stroke="var(--green-text)"
                  strokeWidth={2}
                  dot={{ r: 3, fill: "var(--green-text)" }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          <div className="data-list">
            {earningsSeries.map((row) => (
              <div className="data-list-row" key={row.year}>
                <div>
                  <strong>{row.year}</strong>
                  <div className="meta-row">
                    <span>{currency(row.net_income)} NI</span>
                    <span>{currency(row.free_cash_flow)} FCF</span>
                    {row.divergence ? (
                      <span
                        className={`badge ${
                          row.divergence_direction === "fcf_below_ni"
                            ? "badge--red"
                            : "badge--amber"
                        }`}
                      >
                        Divergence
                      </span>
                    ) : (
                      <span className="badge badge--green">Aligned</span>
                    )}
                  </div>
                </div>
                <CitationLink {...row.citation} />
              </div>
            ))}
          </div>
        </article>

        <article className="card">
          <h2 className="card-title">Debt Maturity Schedule</h2>
          <p className="card-subtitle">
            Principal balances grouped by maturity year.
          </p>

          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={debtMaturity}>
                <CartesianGrid stroke="var(--border2)" vertical={false} />
                <XAxis dataKey="maturity_year" stroke="var(--muted)" />
                <YAxis stroke="var(--muted)" />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="amount" name="Debt Amount" fill="var(--red-text)" />
              </BarChart>
            </ResponsiveContainer>
          </div>

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
        <article className="card">
          <h2 className="card-title">Capital Structure Snapshot</h2>
          {latestCapitalStructure ? (
            <div className="grid-1">
              <div className="kpi">
                <div className="kpi-label">Long-term debt</div>
                <div className="kpi-value">{currency(latestCapitalStructure.long_term_debt)}</div>
              </div>
              <div className="kpi">
                <div className="kpi-label">Total equity</div>
                <div className="kpi-value">{currency(latestCapitalStructure.total_equity)}</div>
              </div>
              <div className="kpi">
                <div className="kpi-label">Free cash flow</div>
                <div className="kpi-value">{currency(latestCapitalStructure.free_cash_flow)}</div>
              </div>
              <CitationLink {...latestCapitalStructure.citation} />
            </div>
          ) : (
            <div className="empty">No capital structure data available.</div>
          )}
        </article>

        <article className="card">
          <h2 className="card-title">D/E Model</h2>
          <p className="card-subtitle">
            Three auto-computed scenarios: Base, Bull, and Bear.
          </p>

          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Scenario</th>
                  <th>Year</th>
                  <th>D/E</th>
                  <th>FCF</th>
                  <th>Refi Rate</th>
                  <th>Covenant</th>
                  <th>Citation</th>
                </tr>
              </thead>
              <tbody>
                {deModel.flatMap((scenario) =>
                  scenario.projections.map((projection) => (
                    <tr key={`${scenario.scenario}-${projection.year}`}>
                      <td>{scenario.scenario}</td>
                      <td>{projection.year}</td>
                      <td>{projection.de_ratio !== null && projection.de_ratio !== undefined ? Number(projection.de_ratio).toFixed(2) : "—"}</td>
                      <td>{currency(projection.fcf)}</td>
                      <td>{percent(projection.refinancing_rate)}</td>
                      <td>
                        {projection.covenant_breach ? (
                          <span className="badge badge--red">Breach</span>
                        ) : (
                          <span className="badge badge--green">Clear</span>
                        )}
                      </td>
                      <td>
                        <CitationLink {...projection.citation} />
                      </td>
                    </tr>
                  )),
                )}
              </tbody>
            </table>
          </div>
        </article>
      </div>

      {earningsSummary?.latest_period ? (
        <article className="card">
          <div className="eyebrow">Latest filing summary</div>
          <div className="meta-row" style={{ marginTop: 8 }}>
            <span>Period: {earningsSummary.latest_period}</span>
            <span>Latest NI: {currency(earningsSummary.latest_net_income)}</span>
            <span>Latest FCF: {currency(earningsSummary.latest_free_cash_flow)}</span>
            <span>
              Recent divergence:{" "}
              {earningsSummary.has_recent_divergence ? (
                <span className="badge badge--red">Yes</span>
              ) : (
                <span className="badge badge--green">No</span>
              )}
            </span>
          </div>
        </article>
      ) : null}
    </section>
  );
}
