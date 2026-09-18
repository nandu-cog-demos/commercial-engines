import { Link } from "react-router-dom";
import { api, EngineComplianceSummary, OperatorComplianceSummary, RagStatus } from "../api";
import { useApi } from "../useApi";

const RAG_CLASS: Record<RagStatus, string> = {
  RED: "rag rag-red",
  AMBER: "rag rag-amber",
  GREEN: "rag rag-green",
};

function RagBadge({ status }: { status: RagStatus }) {
  return <span className={RAG_CLASS[status]}>{status}</span>;
}

function OperatorCard({ operator }: { operator: OperatorComplianceSummary }) {
  return (
    <div>
      <dt>
        {operator.operatorName} <span className="muted">({operator.operatorCode})</span>
      </dt>
      <dd>
        {operator.enginesWithOverdueMandatory}
        <span className="muted"> / {operator.engineCount} engines</span>
      </dd>
      <dd className="sub muted">{operator.overdueMandatorySbCount} overdue mandatory SBs</dd>
    </div>
  );
}

function EngineRow({ engine }: { engine: EngineComplianceSummary }) {
  return (
    <tr>
      <td>
        <RagBadge status={engine.ragStatus} />
      </td>
      <td>
        <Link to={`/engines/${engine.engineId}`}>{engine.serial}</Link>
      </td>
      <td>{engine.family}</td>
      <td>
        {engine.operatorName} <span className="muted">({engine.operatorCode})</span>
      </td>
      <td className="num">{engine.csn.toLocaleString()}</td>
      <td className="num">{engine.applicableSbCount}</td>
      <td className="num">{engine.openSbCount}</td>
      <td className="num">{engine.overdueMandatoryCount}</td>
    </tr>
  );
}

export function FleetCompliancePage() {
  const { data, error, loading } = useApi(() => api.fleetComplianceSummary());

  if (loading) return <p className="muted">Loading fleet compliance…</p>;
  if (error) return <p className="error">{error}</p>;
  if (!data || data.engineCount === 0) return <p className="muted">No engines in the fleet.</p>;

  const engines = data.operators.flatMap((o) => o.engines);

  return (
    <section>
      <div className="page-head">
        <h1>Fleet Compliance</h1>
        <span className="chip cat-mandatory">
          {data.enginesWithOverdueMandatory} of {data.engineCount} engines with overdue mandatory
          SBs
        </span>
      </div>

      <dl className="facts">
        {data.operators.map((o) => (
          <OperatorCard key={o.operatorCode} operator={o} />
        ))}
      </dl>

      <h2 className="section-head">Engines</h2>
      <table>
        <thead>
          <tr>
            <th>Status</th>
            <th>Serial</th>
            <th>Family</th>
            <th>Operator</th>
            <th className="num">CSN</th>
            <th className="num">Applicable SBs</th>
            <th className="num">Open</th>
            <th className="num">Overdue mandatory</th>
          </tr>
        </thead>
        <tbody>
          {engines.map((e) => (
            <EngineRow key={e.engineId} engine={e} />
          ))}
        </tbody>
      </table>
    </section>
  );
}
