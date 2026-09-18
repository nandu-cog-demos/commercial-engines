"""SB applicability and per-engine compliance rules (NO-196)."""

from . import models
from .schemas import BlockingSb, EngineComplianceRow


def serial_suffix(serial: str) -> int:
    """`TF9-001234` -> 1234, `TF7X-000100` -> 100."""
    return int(serial.rsplit("-", 1)[-1])


def parse_ranges(ranges: str) -> list[tuple[int, int]]:
    """`"000500-000900,001200-001300"` -> `[(500, 900), (1200, 1300)]`."""
    out: list[tuple[int, int]] = []
    for part in ranges.split(","):
        part = part.strip()
        if not part:
            continue
        start, end = part.split("-", 1)
        out.append((int(start), int(end)))
    return out


def is_applicable(sb: models.ServiceBulletin, engine: models.Engine) -> bool:
    if sb.family != engine.family:
        return False
    suffix = serial_suffix(engine.serial)
    return any(start <= suffix <= end for start, end in parse_ranges(sb.applicability_ranges))


def compliance_rows(
    engine: models.Engine, sbs: list[models.ServiceBulletin]
) -> list[EngineComplianceRow]:
    records = {c.sb_id: c.status for c in engine.compliance}
    rows: list[EngineComplianceRow] = []
    for sb in sorted(sbs, key=lambda s: s.sb_number):
        if not is_applicable(sb, engine):
            continue
        status = records.get(sb.id, models.ComplianceStatus.OPEN)
        remaining = (
            sb.compliance_deadline_cycles - engine.csn
            if sb.compliance_deadline_cycles is not None
            else None
        )
        complied = status == models.ComplianceStatus.COMPLIED
        overdue = remaining is not None and remaining < 0 and not complied
        rows.append(
            EngineComplianceRow(
                sbNumber=sb.sb_number, title=sb.title, category=sb.category, status=sb.status,
                complianceStatus=status, complianceDeadlineCycles=sb.compliance_deadline_cycles,
                cyclesRemaining=remaining, overdue=overdue, relatedAdNumber=sb.related_ad_number,
            )
        )
    return rows


def overdue_mandatory_count(rows: list[EngineComplianceRow]) -> int:
    return sum(1 for r in rows if r.overdue and r.category == models.SbCategory.MANDATORY)


def blocking_sbs(rows: list[EngineComplianceRow]) -> list[BlockingSb]:
    """Only ACTIVE, MANDATORY, OPEN and overdue SBs gate a release."""
    return [
        BlockingSb(sbNumber=r.sbNumber, title=r.title)
        for r in rows
        if r.overdue
        and r.category == models.SbCategory.MANDATORY
        and r.status == models.SbStatus.ACTIVE
        and r.complianceStatus == models.ComplianceStatus.OPEN
    ]
