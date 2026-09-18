import { useState } from "react";
import { api, releaseBlockedDetail, ReleaseBlockedDetail, ShopVisit } from "../api";
import { useApi } from "../useApi";

export function ShopVisitsPage() {
  const { data, error, loading } = useApi(() => api.shopVisits());
  const [released, setReleased] = useState<Record<number, ShopVisit>>({});
  const [blocked, setBlocked] = useState<{ visit: ShopVisit; detail: ReleaseBlockedDetail } | null>(
    null,
  );
  const [releaseError, setReleaseError] = useState<string | null>(null);

  if (loading) return <p className="muted">Loading shop visits…</p>;
  if (error) return <p className="error">{error}</p>;

  async function release(visit: ShopVisit) {
    const releasedBy = window.prompt(`Release ${visit.engineSerial} — released by:`);
    if (!releasedBy) return;
    setReleaseError(null);
    try {
      const updated = await api.releaseShopVisit(visit.id, releasedBy);
      setReleased((prev) => ({ ...prev, [visit.id]: updated }));
    } catch (err) {
      const detail = releaseBlockedDetail(err);
      if (detail) setBlocked({ visit, detail });
      else setReleaseError((err as Error).message);
    }
  }

  const visits = (data ?? []).map((v) => released[v.id] ?? v);

  return (
    <section>
      <div className="page-head">
        <h1>Shop Visits</h1>
      </div>
      {releaseError && <p className="error">{releaseError}</p>}
      <table>
        <thead>
          <tr>
            <th>Engine</th>
            <th>Shop</th>
            <th>Workscope</th>
            <th>Inducted</th>
            <th>Status</th>
            <th>Released</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {visits.map((v) => (
            <tr key={v.id}>
              <td>{v.engineSerial}</td>
              <td>{v.shop}</td>
              <td>{v.workscope}</td>
              <td>{v.inductedOn}</td>
              <td>{v.status}</td>
              <td>
                {v.status === "RELEASED"
                  ? `${v.releasedBy ?? "—"} · ${v.releasedAt?.slice(0, 10) ?? ""}`
                  : "—"}
              </td>
              <td className="num">
                {v.status !== "RELEASED" && (
                  <button className="btn" onClick={() => release(v)}>
                    Release
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {blocked && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Release blocked">
          <div className="modal">
            <h2>Release blocked</h2>
            <p>
              {blocked.visit.engineSerial}: {blocked.detail.message}
            </p>
            <ul className="blocking-list">
              {blocked.detail.blockingSbs.map((sb) => (
                <li key={sb.sbNumber}>
                  <strong>{sb.sbNumber}</strong> — {sb.title}
                </li>
              ))}
            </ul>
            <button className="btn" onClick={() => setBlocked(null)}>
              Close
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
