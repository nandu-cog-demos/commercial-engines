import enum
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from .models import ComplianceStatus, SbCategory, SbStatus, ShopVisitStatus


class AdBannerState(str, enum.Enum):
    RED = "RED"
    AMBER = "AMBER"
    GREEN = "GREEN"


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class EngineOut(ApiModel):
    id: int
    serial: str
    family: str
    operatorCode: str
    operatorName: str
    csn: int
    tsn: int
    position: str | None

    @classmethod
    def from_orm_engine(cls, e) -> "EngineOut":
        return cls(
            id=e.id, serial=e.serial, family=e.family, operatorCode=e.operator_code,
            operatorName=e.operator_name, csn=e.csn, tsn=e.tsn, position=e.position,
        )


class ServiceBulletinOut(ApiModel):
    id: int
    sbNumber: str
    title: str
    family: str
    category: SbCategory
    status: SbStatus
    applicabilityRanges: str
    complianceDeadlineCycles: int | None
    relatedAdNumber: str | None
    issuedOn: date
    summary: str | None

    @classmethod
    def from_orm_sb(cls, s) -> "ServiceBulletinOut":
        return cls(
            id=s.id, sbNumber=s.sb_number, title=s.title, family=s.family, category=s.category,
            status=s.status, applicabilityRanges=s.applicability_ranges,
            complianceDeadlineCycles=s.compliance_deadline_cycles,
            relatedAdNumber=s.related_ad_number, issuedOn=s.issued_on, summary=s.summary,
        )


class SbComplianceOut(ApiModel):
    id: int
    engineId: int
    sbId: int
    sbNumber: str
    status: ComplianceStatus
    compliedDate: date | None
    compliedAtCsn: int | None

    @classmethod
    def from_orm_row(cls, c) -> "SbComplianceOut":
        return cls(
            id=c.id, engineId=c.engine_id, sbId=c.sb_id, sbNumber=c.service_bulletin.sb_number,
            status=c.status, compliedDate=c.complied_date, compliedAtCsn=c.complied_at_csn,
        )


class AdDirectiveOut(ApiModel):
    sbId: int
    sbNumber: str
    adNumber: str | None
    title: str
    complianceStatus: ComplianceStatus
    complianceDeadlineCycles: int | None
    cyclesRemaining: int | None
    overdue: bool


class EngineAdStatusOut(ApiModel):
    engineId: int
    serial: str
    csn: int
    state: AdBannerState
    overdueCount: int
    dueSoonCount: int
    directives: list[AdDirectiveOut]


class ShopVisitOut(ApiModel):
    id: int
    engineId: int
    engineSerial: str
    shop: str
    workscope: str
    inductedOn: date
    status: ShopVisitStatus
    releasedAt: datetime | None
    releasedBy: str | None

    @classmethod
    def from_orm_sv(cls, v) -> "ShopVisitOut":
        return cls(
            id=v.id, engineId=v.engine_id, engineSerial=v.engine.serial, shop=v.shop,
            workscope=v.workscope, inductedOn=v.inducted_on, status=v.status,
            releasedAt=v.released_at, releasedBy=v.released_by,
        )


class ReleaseRequest(BaseModel):
    releasedBy: str
