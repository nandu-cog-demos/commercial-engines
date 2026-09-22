"""Applicability and airworthiness-directive state for an engine.

Rules come from `docs/tickets/CES-482-engine-compliance-view-and-release-gate.md`.
"""

from dataclasses import dataclass

from . import models


def serial_suffix(serial: str) -> int | None:
    """Numeric suffix of an engine serial: ``TF9-001234`` -> ``1234``."""
    tail = serial.rsplit("-", 1)[-1]
    return int(tail) if tail.isdigit() else None


def parse_ranges(ranges: str) -> list[tuple[int, int]]:
    """Parse ``"001000-001500,002200-002400"`` into inclusive integer pairs."""
    parsed: list[tuple[int, int]] = []
    for part in ranges.split(","):
        part = part.strip()
        if not part:
            continue
        start, _, end = part.partition("-")
        if start.strip().isdigit() and end.strip().isdigit():
            parsed.append((int(start), int(end)))
    return parsed


def serial_in_ranges(serial: str, ranges: str) -> bool:
    suffix = serial_suffix(serial)
    if suffix is None:
        return False
    return any(start <= suffix <= end for start, end in parse_ranges(ranges))


def is_applicable(engine: models.Engine, sb: models.ServiceBulletin) -> bool:
    """Family match, serial inside one of the SB's ranges, SB not terminated."""
    return (
        sb.family == engine.family
        and sb.status != models.SbStatus.TERMINATED
        and serial_in_ranges(engine.serial, sb.applicability_ranges)
    )


@dataclass
class DirectiveState:
    sb: models.ServiceBulletin
    compliance_status: models.ComplianceStatus
    cycles_remaining: int | None
    overdue: bool


def directive_states(
    engine: models.Engine,
    bulletins: list[models.ServiceBulletin],
    compliance: dict[int, models.ComplianceStatus],
) -> list[DirectiveState]:
    """Open mandatory ADs applicable to the engine, worst (most overdue) first."""
    states: list[DirectiveState] = []
    for sb in bulletins:
        if sb.category != models.SbCategory.MANDATORY or not is_applicable(engine, sb):
            continue
        status = compliance.get(sb.id, models.ComplianceStatus.OPEN)
        if status != models.ComplianceStatus.OPEN:
            continue
        remaining = (
            None if sb.compliance_deadline_cycles is None
            else sb.compliance_deadline_cycles - engine.csn
        )
        states.append(
            DirectiveState(
                sb=sb,
                compliance_status=status,
                cycles_remaining=remaining,
                overdue=remaining is not None and remaining <= 0,
            )
        )
    states.sort(key=lambda s: (s.cycles_remaining is None, s.cycles_remaining or 0, s.sb.sb_number))
    return states
