import { useState } from "react";
import { useParams } from "react-router-dom";
import { api, type AdDirective, type EngineAdStatus } from "../api";
import { useApi } from "../useApi";

type Tab = "overview" | "sb-records" | "shop-visits";

const BANNER: Record<EngineAdStatus["state"], { className: string; label: string }> = {
  RED: { className: "banner-red", label: "Airworthiness directives — action required" },
  AMBER: { className: "banner-amber", label: "Airworthiness directives — due soon" },
  GREEN: { className: "banner-green", label: "Airworthiness directives — clear" },
};

function cyclesLabel(d: AdDirective): string {
  if (d.cyclesRemaining === null) return "no cycle deadline";
  if (d.overdue) return `overdue by ${Math.abs(d.cyclesRemaining).toLocaleString()} cycles`;
  return `${d.cyclesRemaining.toLocaleString()} cycles remaining`;
}

function AdStatusBanner({ status }: { status: EngineAdStatus }) {
  const { className, label } = BANNER[status.state];
  return (
    <section className={`ad-banner ${className}`} aria-label="Airworthiness directive status">
      <h2 className="ad-banner-head">
        <span className="ad-banner-dot" aria-hidden="true" />
        <span className="ad-banner-label">{label}</span>
        <span className="ad-banner-headline">{status.headline}</span>
      </h2>
      {status.directives.length > 0 && (
        <ul className="ad-banner-list">
          {status.directives.map((d) => (
            <li key={d.sbNumber}>
              <span className="ad-banner-ad">{d.relatedAdNumber ?? "No AD"}</span>
              <span className="ad-banner-sb">SB {d.sbNumber}</span>
              <span className="ad-banner-title">{d.title}</span>
              <span className="ad-banner-cycles">{cyclesLabel(d)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function EngineDetailPage() {
  const { id } = useParams();
  const engineId = Number(id);
  const [tab, setTab] = useState<Tab>("overview");
  const engine = useApi(() => api.engine(engineId), [engineId]);
  const adStatus = useApi(() => api.engineAdStatus(engineId), [engineId]);
  const records = useApi(() => api.engineSbRecords(engineId), [engineId]);
  const visits = useApi(() => api.engineShopVisits(engineId), [engineId]);

  if (engine.loading) return <p className="muted">Loading engine…</p>;
  if (engine.error || !engine.data) return <p className="error">{engine.error ?? "Not found"}</p>;

  const e = engine.data;

  return (
    <section>
      <div className="page-head">
        <h1>{e.serial}</h1>
        <span className="chip">{e.family}</span>
      </div>
      <p className="muted">
        {e.operatorName} ({e.operatorCode}) · {e.position ?? "unassigned"}
      </p>

      {adStatus.loading && <p className="muted">Loading airworthiness directive status…</p>}
      {adStatus.error && <p className="error">{adStatus.error}</p>}
      {adStatus.data && <AdStatusBanner status={adStatus.data} />}

      <div className="tabs">
        <button className={tab === "overview" ? "active" : ""} onClick={() => setTab("overview")}>
          Overview
        </button>
        <button
          className={tab === "sb-records" ? "active" : ""}
          onClick={() => setTab("sb-records")}
        >
          SB Records
        </button>
        <button
          className={tab === "shop-visits" ? "active" : ""}
          onClick={() => setTab("shop-visits")}
        >
          Shop Visits
        </button>
      </div>

      {tab === "overview" && (
        <dl className="facts">
          <div>
            <dt>Cycles since new</dt>
            <dd>{e.csn.toLocaleString()}</dd>
          </div>
          <div>
            <dt>Hours since new</dt>
            <dd>{e.tsn.toLocaleString()}</dd>
          </div>
          <div>
            <dt>Operator</dt>
            <dd>{e.operatorName}</dd>
          </div>
          <div>
            <dt>Position</dt>
            <dd>{e.position ?? "—"}</dd>
          </div>
        </dl>
      )}

      {tab === "sb-records" && (
        <table>
          <thead>
            <tr>
              <th>SB</th>
              <th>Status</th>
              <th>Complied</th>
              <th className="num">At CSN</th>
            </tr>
          </thead>
          <tbody>
            {(records.data ?? []).map((r) => (
              <tr key={r.id}>
                <td>{r.sbNumber}</td>
                <td>{r.status}</td>
                <td>{r.compliedDate ?? "—"}</td>
                <td className="num">{r.compliedAtCsn?.toLocaleString() ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {tab === "shop-visits" && (
        <table>
          <thead>
            <tr>
              <th>Shop</th>
              <th>Workscope</th>
              <th>Inducted</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {(visits.data ?? []).map((v) => (
              <tr key={v.id}>
                <td>{v.shop}</td>
                <td>{v.workscope}</td>
                <td>{v.inductedOn}</td>
                <td>{v.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
