import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

const RECENT_KEY = "edgarian-recent-searches";

function readRecentSearches() {
  try {
    const raw = window.localStorage.getItem(RECENT_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeRecentSearch(symbol) {
  const existing = readRecentSearches().filter((item) => item !== symbol);
  const next = [symbol, ...existing].slice(0, 8);
  window.localStorage.setItem(RECENT_KEY, JSON.stringify(next));
}

export default function Landing() {
  const navigate = useNavigate();
  const [symbol, setSymbol] = useState("");
  const recentSearches = useMemo(() => readRecentSearches(), []);

  const onSubmit = (event) => {
    event.preventDefault();
    const normalized = symbol.trim().toUpperCase();
    if (!normalized) {
      return;
    }
    writeRecentSearch(normalized);
    navigate(`/company/${normalized}`);
  };

  return (
    <main className="page">
      <section className="search-shell">
        <div>
          <div className="eyebrow">Research any public company</div>
          <h1 className="headline">One page for earnings, business, and filings.</h1>
          <p className="card-subtitle">Powered by SEC EDGAR public filings</p>

          <form className="search-form" onSubmit={onSubmit}>
            <input
              className="search-input"
              type="text"
              placeholder="Enter ticker symbol, e.g. AAPL"
              value={symbol}
              onChange={(event) => setSymbol(event.target.value)}
            />
            <button className="search-button" type="submit">
              Open company page
            </button>
          </form>

          <div className="card" style={{ marginTop: 20 }}>
            <div className="eyebrow">Recent searches</div>
            {recentSearches.length === 0 ? (
              <div className="empty">No recent searches yet.</div>
            ) : (
              <div className="meta-row" style={{ marginTop: 12 }}>
                {recentSearches.map((item) => (
                  <button
                    key={item}
                    className="mode-btn"
                    type="button"
                    onClick={() => navigate(`/company/${item}`)}
                  >
                    {item}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}
