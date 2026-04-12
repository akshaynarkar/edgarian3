import React from "react";
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

export default function Business({ sankeyPayload, sankeyHtml, segments }) {
  return (
    <section className="grid-1">
      <article className="card">
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
          <div>
            <h2 className="card-title">Business Flow Sankey</h2>
            <p className="card-subtitle">
              Revenue to profit bridge rendered from canonical Sankey payload.
            </p>
          </div>
          <CitationLink {...sankeyPayload?.citation} />
        </div>

        <div className="iframe-shell" style={{ marginTop: 16 }}>
          <iframe
            title={`${sankeyPayload?.ticker || "Company"} Sankey`}
            srcDoc={sankeyHtml}
            sandbox="allow-scripts"
          />
        </div>
      </article>

      <article className="card">
        <h2 className="card-title">Segment Table</h2>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Segment</th>
                <th>Current Period</th>
                <th>Current Revenue</th>
                <th>Prior Period</th>
                <th>Prior Revenue</th>
                <th>YoY Delta</th>
                <th>Citation</th>
              </tr>
            </thead>
            <tbody>
              {segments.map((row) => (
                <tr key={`${row.current_period}-${row.segment_name}`}>
                  <td>{row.segment_name}</td>
                  <td>{row.current_period}</td>
                  <td>{currency(row.current_revenue)}</td>
                  <td>{row.prior_period || "—"}</td>
                  <td>{currency(row.prior_revenue)}</td>
                  <td>{percent(row.yoy_delta_pct)}</td>
                  <td>
                    <CitationLink {...row.citation} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
    </section>
  );
}
