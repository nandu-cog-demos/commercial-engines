export type SbCategory = "OPTIONAL" | "RECOMMENDED" | "MANDATORY";
export type SbStatus = "ACTIVE" | "SUPERSEDED" | "TERMINATED";
export type ComplianceStatus = "OPEN" | "COMPLIED" | "NOT_APPLICABLE";
export type ShopVisitStatus = "INDUCTED" | "IN_WORK" | "RELEASED";

export interface Engine {
  id: number;
  serial: string;
  family: string;
  operatorCode: string;
  operatorName: string;
  csn: number;
  tsn: number;
  position: string | null;
  overdueMandatoryCount: number;
}

export interface ServiceBulletin {
  id: number;
  sbNumber: string;
  title: string;
  family: string;
  category: SbCategory;
  status: SbStatus;
  applicabilityRanges: string;
  complianceDeadlineCycles: number | null;
  relatedAdNumber: string | null;
  issuedOn: string;
  summary: string | null;
}

export interface SbRecord {
  id: number;
  engineId: number;
  sbId: number;
  sbNumber: string;
  status: ComplianceStatus;
  compliedDate: string | null;
  compliedAtCsn: number | null;
}

export interface ShopVisit {
  id: number;
  engineId: number;
  engineSerial: string;
  shop: string;
  workscope: string;
  inductedOn: string;
  status: ShopVisitStatus;
  releasedAt: string | null;
  releasedBy: string | null;
}

export interface EngineComplianceRow {
  sbNumber: string;
  title: string;
  category: SbCategory;
  status: SbStatus;
  complianceStatus: ComplianceStatus;
  complianceDeadlineCycles: number | null;
  cyclesRemaining: number | null;
  overdue: boolean;
  relatedAdNumber: string | null;
}

export interface BlockingSb {
  sbNumber: string;
  title: string;
}

export interface ReleaseBlockedDetail {
  message: string;
  blockingSbs: BlockingSb[];
}

export function releaseBlockedDetail(err: unknown): ReleaseBlockedDetail | null {
  if (!(err instanceof ApiError) || err.status !== 409) return null;
  const detail = (err.body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "object" && detail !== null && "blockingSbs" in detail) {
    return detail as ReleaseBlockedDetail;
  }
  return null;
}

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown) {
    super(`API error ${status}`);
    this.status = status;
    this.body = body;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api/v1${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  const body = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, body);
  return body as T;
}

export const api = {
  engines: () => request<Engine[]>("/engines"),
  engine: (id: number) => request<Engine>(`/engines/${id}`),
  engineSbRecords: (id: number) => request<SbRecord[]>(`/engines/${id}/sb-records`),
  engineCompliance: (id: number) =>
    request<EngineComplianceRow[]>(`/engines/${id}/compliance`),
  engineShopVisits: (id: number) => request<ShopVisit[]>(`/engines/${id}/shop-visits`),
  serviceBulletins: () => request<ServiceBulletin[]>("/service-bulletins"),
  shopVisits: () => request<ShopVisit[]>("/shop-visits"),
  releaseShopVisit: (id: number, releasedBy: string) =>
    request<ShopVisit>(`/shop-visits/${id}/release`, {
      method: "POST",
      body: JSON.stringify({ releasedBy }),
    }),
};
