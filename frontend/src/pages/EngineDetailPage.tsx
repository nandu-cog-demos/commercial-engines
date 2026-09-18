import { useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";
import { useApi } from "../useApi";

type Tab = "overview" | "compliance" | "sb-records" | "shop-visits";

export function EngineDetailPage() {
  const { id } = useParams();
  const engineId = Number(id);
  const [tab, setTab] = useState<Tab>("overview");
  const engine = useApi(() => api.engine(engineId), [engineId]);
  const compliance = useApi(() => api.engineCompliance(engineId), [engineId]);
  const records = useApi(() => api.engineSbRecords(engineId), [engineId]);
  const visits = useApi(() => api.engineShopVisits(engineId), [engineId]);

  if (engine.loading) return <p className="muted">Loading engine…</p>;
  if (engine.error || !engine.data) return <p className="error">{engine.error ?? "Not found"}</p>;

  const e = engine.data;
  const complianceRows = compliance.data ?? [];
  const overdueCount = complianceRows.filter((r) => r.overdue).length;

  return (
    <section>
      <div className="page-head">
        <h1>{e.serial}</h1>
        <span className="chip">{e.family}</span>
      </div>
      <p className="muted">
        {e.operatorName} ({e.operatorCode}) · {e.position ?? "unassigned"}
      </p>

      <div className="tabs">
        <button className={tab === "overview" ? "active" : ""} onClick={() => setTab("overview")}>
          Overview
        </button>
        <button
          className={tab === "compliance" ? "active" : ""}
          onClick={() => setTab("compliance")}
        >
          Compliance
          {overdueCount > 0 && <span className="badge">{overdueCount}</span>}
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

      {tab === "compliance" &&
        (compliance.error ? (
          <p className="error">{compliance.error}</p>
        ) : complianceRows.length === 0 ? (
          <p className="muted">No applicable service bulletins</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>SB</th>
                <th>Title</th>
                <th>Category</th>
                <th>SB Status</th>
                <th>Compliance</th>
                <th className="num">Deadline</th>
                <th className="num">Cycles Remaining</th>
                <th>AD</th>
              </tr>
            </thead>
            <tbody>
              {complianceRows.map((r) => (
                <tr key={r.sbNumber} className={r.overdue ? "overdue" : ""}>
                  <td>{r.sbNumber}</td>
                  <td>{r.title}</td>
                  <td>
                    <span className={`chip cat-${r.category.toLowerCase()}`}>{r.category}</span>
                  </td>
                  <td>{r.status}</td>
                  <td>
                    {r.complianceStatus}
                    {r.overdue && <span className="chip chip-overdue">OVERDUE</span>}
                  </td>
                  <td className="num">{r.complianceDeadlineCycles?.toLocaleString() ?? "—"}</td>
                  <td className="num">{r.cyclesRemaining?.toLocaleString() ?? "—"}</td>
                  <td>{r.relatedAdNumber ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ))}

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
