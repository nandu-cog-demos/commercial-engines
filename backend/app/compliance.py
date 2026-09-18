"""Applicability and overdue rules for service bulletins against engines."""

import re
from dataclasses import dataclass

from .models import ComplianceStatus, Engine, SbCategory, SbStatus, ServiceBulletin

RAG_RED = "RED"
RAG_AMBER = "AMBER"
RAG_GREEN = "GREEN"

_SUFFIX_RE = re.compile(r"(\d+)$")


@dataclass(frozen=True)
class ApplicableSb:
    """An SB that applies to an engine, with the engine's compliance state folded in."""

    service_bulletin: ServiceBulletin
    compliance_status: ComplianceStatus
    cycles_remaining: int | None
    overdue: bool

    @property
    def blocks_release(self) -> bool:
        sb = self.service_bulletin
        return (
            sb.category == SbCategory.MANDATORY
            and sb.status == SbStatus.ACTIVE
            and self.compliance_status == ComplianceStatus.OPEN
            and self.overdue
        )


def parse_applicability_ranges(raw: str) -> list[tuple[int, int]]:
    """Parse comma-separated inclusive ranges, e.g. "001000-001500,002200-002400"."""
    ranges: list[tuple[int, int]] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        start, _, end = part.partition("-")
        ranges.append((int(start), int(end)))
    return ranges


def serial_suffix(serial: str) -> int | None:
    """Numeric suffix of an engine serial, e.g. "TF9-001234" -> 1234."""
    match = _SUFFIX_RE.search(serial)
    return int(match.group(1)) if match else None


def sb_applies_to_engine(sb: ServiceBulletin, engine: Engine) -> bool:
    if sb.family != engine.family:
        return False
    suffix = serial_suffix(engine.serial)
    if suffix is None:
        return False
    ranges = parse_applicability_ranges(sb.applicability_ranges)
    return any(start <= suffix <= end for start, end in ranges)


def applicable_sbs(
    engine: Engine,
    service_bulletins: list[ServiceBulletin],
    compliance_by_sb_id: dict[int, ComplianceStatus],
) -> list[ApplicableSb]:
    rows: list[ApplicableSb] = []
    for sb in service_bulletins:
        if not sb_applies_to_engine(sb, engine):
            continue
        status = compliance_by_sb_id.get(sb.id, ComplianceStatus.OPEN)
        remaining = (
            None
            if sb.compliance_deadline_cycles is None
            else sb.compliance_deadline_cycles - engine.csn
        )
        overdue = (
            remaining is not None and remaining < 0 and status != ComplianceStatus.COMPLIED
        )
        rows.append(
            ApplicableSb(
                service_bulletin=sb,
                compliance_status=status,
                cycles_remaining=remaining,
                overdue=overdue,
            )
        )
    return rows


def rag_status(rows: list[ApplicableSb]) -> str:
    """RED when an active mandatory SB is overdue, AMBER when anything applicable is still open."""
    if any(row.blocks_release for row in rows):
        return RAG_RED
    if any(
        row.service_bulletin.status == SbStatus.ACTIVE
        and row.compliance_status == ComplianceStatus.OPEN
        for row in rows
    ):
        return RAG_AMBER
    return RAG_GREEN
