import { useState } from "react";
import { useParams } from "react-router-dom";
import { api, type AdDirective, type EngineAdStatus } from "../api";
import { useApi } from "../useApi";

type Tab = "overview" | "sb-records" | "shop-visits";

const BANNER_CLASS = { RED: "ad-red", AMBER: "ad-amber", GREEN: "ad-green" } as const;

function headline(s: EngineAdStatus) {
  const csn = s.csn.toLocaleString();
  if (s.state === "RED") {
    const n = s.overdueCount;
    return ["Airworthiness directives — action required", `${n} mandatory AD${n === 1 ? "" : "s"} overdue at CSN ${csn}`];
  }
  if (s.state === "AMBER") {
    const n = s.dueSoonCount;
    return ["Airworthiness directives — due soon", `${n} mandatory AD${n === 1 ? "" : "s"} open at CSN ${csn}`];
  }
  return ["Airworthiness directives — clear", `No mandatory AD open at CSN ${csn}`];
}

function cyclesLabel(d: AdDirective) {
  if (d.cyclesRemaining === null) return "no cycle deadline";
  return d.overdue
    ? `overdue by ${Math.abs(d.cyclesRemaining).toLocaleString()} cycles`
    : `${d.cyclesRemaining.toLocaleString()} cycles remaining`;
}

function AdStatusBanner({ status }: { status: EngineAdStatus }) {
  const [title, subtitle] = headline(status);
  return (
    <div className={`ad-banner ${BANNER_CLASS[status.state]}`}>
      <div className="ad-banner-head">
        <span className="ad-dot" />
        <strong>{title}</strong>
        <span className="muted">{subtitle}</span>
      </div>
      {status.directives.map((d) => (
        <div className="ad-row" key={d.sbId}>
          <strong>{d.adNumber ?? d.sbNumber}</strong>
          <span className="muted">SB {d.sbNumber}</span>
          <span>{d.title}</span>
          <span className="ad-cycles">{cyclesLabel(d)}</span>
        </div>
      ))}
    </div>
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
