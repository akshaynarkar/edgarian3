import React, { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import EarningsQuality from "../components/tabs/EarningsQuality.jsx";
import Business from "../components/tabs/Business.jsx";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const TABS = [
  { key: "earnings", label: "Earnings Quality" },
  { key: "business", label: "Business" },
];

export default function Company() {
  const { symbol } = useParams();
  const [activeTab, setActiveTab] = useState("earnings");
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorText, setErrorText] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function fetchCompany() {
      try {
        setLoading(true);
        setErrorText("");

        const response = await fetch(`${API_BASE_URL}/company/${symbol}`, {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Request failed with ${response.status}`);
        }

        const data = await response.json();
        setPayload(data);

        const normalized = symbol.toUpperCase();
        const key = "edgarian-recent-searches";
        const existing = JSON.parse(window.localStorage.getItem(key) || "[]");
        const next = [normalized, ...existing.filter((item) => item !== normalized)].slice(0, 8);
        window.localStorage.setItem(key, JSON.stringify(next));
      } catch (error) {
        if (error.name !== "AbortError") {
          setErrorText(error.message || "Unable to load company data.");
        }
      } finally {
        setLoading(false);
      }
    }

    fetchCompany();

    return () => controller.abort();
  }, [symbol]);

  const company = payload?.company;
  const earnings = payload?.tabs?.earnings_quality;
  const debt = payload?.tabs?.debt;
  const business = payload?.tabs?.business;

  const headerPrice = useMemo(() => {
    if (!company?.price) {
      return "Price unavailable";
    }
    return `$${Number(company.price).toLocaleString(undefined, {
      maximumFractionDigits: 2,
      minimumFractionDigits: 2,
    })}`;
  }, [company]);

  if (loading) {
    return <main className="page"><div className="loading">Loading {symbol?.toUpperCase()}…</div></main>;
  }

  if (errorText) {
    return <main className="page"><div className="error">{errorText}</div></main>;
  }

  return (
    <main className="page page--tight">
      <section className="card">
        <div className="eyebrow">Company research page</div>
        <h1 className="headline" style={{ marginBottom: 6 }}>
          {company?.name || symbol?.toUpperCase()}
        </h1>
        <div className="meta-row" style={{ marginBottom: 10 }}>
          <span>{company?.symbol}</span>
          <span>·</span>
          <span>{company?.sector || "Sector unavailable"}</span>
          <span>·</span>
          <span>{company?.exchange || "Exchange unavailable"}</span>
        </div>
        <div className="meta-row">
          <strong style={{ color: "var(--text)" }}>{headerPrice}</strong>
          <span>{company?.price_label}</span>
        </div>
      </section>

      <div className="tab-row">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            className={`tab-btn ${activeTab === tab.key ? "is-active" : ""}`}
            type="button"
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "earnings" ? (
        <EarningsQuality
          earningsSeries={earnings?.series || []}
          earningsSummary={earnings?.summary || {}}
          debtMaturity={debt?.debt_maturity || []}
          deModel={debt?.de_model || []}
          latestCapitalStructure={debt?.latest_capital_structure || null}
        />
      ) : null}

      {activeTab === "business" ? (
        <Business
          sankeyPayload={business?.sankey_payload || {}}
          sankeyHtml={business?.sankey_html || ""}
          segments={business?.segments || []}
        />
      ) : null}
    </main>
  );
}
