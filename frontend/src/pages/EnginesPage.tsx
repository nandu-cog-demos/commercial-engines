import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useApi } from "../useApi";

export function EnginesPage() {
  const { data, error, loading } = useApi(() => api.engines());
  const [filter, setFilter] = useState("");

  if (loading) return <p className="muted">Loading engines…</p>;
  if (error) return <p className="error">{error}</p>;

  const engines = (data ?? []).filter((e) =>
    `${e.serial} ${e.operatorName} ${e.family}`.toLowerCase().includes(filter.toLowerCase()),
  );

  return (
    <section>
      <div className="page-head">
        <h1>Engines</h1>
        <input
          placeholder="Filter by serial, operator or family"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>
      <table>
        <thead>
          <tr>
            <th>Serial</th>
            <th>Family</th>
            <th>Operator</th>
            <th className="num">CSN</th>
            <th className="num">TSN</th>
            <th>Position</th>
          </tr>
        </thead>
        <tbody>
          {engines.map((e) => (
            <tr key={e.id}>
              <td>
                <Link to={`/engines/${e.id}`}>{e.serial}</Link>
                {e.overdueMandatoryCount > 0 && (
                  <span className="badge" title="Overdue mandatory service bulletins">
                    {e.overdueMandatoryCount} overdue
                  </span>
                )}
              </td>
              <td>{e.family}</td>
              <td>
                {e.operatorName} <span className="muted">({e.operatorCode})</span>
              </td>
              <td className="num">{e.csn.toLocaleString()}</td>
              <td className="num">{e.tsn.toLocaleString()}</td>
              <td>{e.position ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
