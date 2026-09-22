"""Airworthiness-directive position of an engine: which SBs apply, and how the
engine sits against their cycle deadlines."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .models import (
    AdBannerState,
    ComplianceStatus,
    Engine,
    SbCategory,
    SbCompliance,
    SbStatus,
    ServiceBulletin,
)


@dataclass(frozen=True)
class AdItem:
    sb_number: str
    title: str
    category: SbCategory
    compliance_status: ComplianceStatus
    related_ad_number: str | None
    deadline_cycles: int | None
    cycles_remaining: int | None
    overdue: bool


@dataclass(frozen=True)
class AdStatus:
    engine: Engine
    state: AdBannerState
    headline: str
    overdue_count: int
    open_count: int
    directives: list[AdItem]


def serial_suffix(serial: str) -> int | None:
    """Numeric part after the family prefix, e.g. ``TF9-001234`` -> ``1234``."""
    _, _, tail = serial.partition("-")
    return int(tail) if tail.isdigit() else None


def serial_in_ranges(serial: str, ranges: str) -> bool:
    """``ranges`` is comma-separated inclusive ``start-end`` pairs."""
    suffix = serial_suffix(serial)
    if suffix is None:
        return False
    for part in ranges.split(","):
        start, sep, end = part.strip().partition("-")
        if not sep or not start.strip().isdigit() or not end.strip().isdigit():
            continue
        if int(start) <= suffix <= int(end):
            return True
    return False


def applies_to(sb: ServiceBulletin, engine: Engine) -> bool:
    return (
        sb.family == engine.family
        and sb.status is not SbStatus.TERMINATED
        and serial_in_ranges(engine.serial, sb.applicability_ranges)
    )


def _headline(state: AdBannerState, count: int, csn: int) -> str:
    cycles = f"CSN {csn:,}"
    plural = "AD" if count == 1 else "ADs"
    if state is AdBannerState.RED:
        return f"{count} mandatory {plural} overdue at {cycles}"
    if state is AdBannerState.AMBER:
        return f"{count} mandatory {plural} open, none overdue at {cycles}"
    return f"No mandatory AD open at {cycles}"


def ad_status(engine: Engine, db: Session) -> AdStatus:
    bulletins = db.scalars(
        select(ServiceBulletin)
        .where(ServiceBulletin.family == engine.family)
        .order_by(ServiceBulletin.sb_number)
    ).all()
    records = {
        c.sb_id: c
        for c in db.scalars(
            select(SbCompliance)
            .options(selectinload(SbCompliance.service_bulletin))
            .where(SbCompliance.engine_id == engine.id)
        ).all()
    }

    directives: list[AdItem] = []
    for sb in bulletins:
        if not applies_to(sb, engine) or sb.category is not SbCategory.MANDATORY:
            continue
        record = records.get(sb.id)
        status = record.status if record is not None else ComplianceStatus.OPEN
        if status is not ComplianceStatus.OPEN:
            continue
        deadline = sb.compliance_deadline_cycles
        remaining = None if deadline is None else deadline - engine.csn
        directives.append(
            AdItem(
                sb_number=sb.sb_number,
                title=sb.title,
                category=sb.category,
                compliance_status=status,
                related_ad_number=sb.related_ad_number,
                deadline_cycles=deadline,
                cycles_remaining=remaining,
                overdue=remaining is not None and remaining <= 0,
            )
        )

    directives.sort(key=lambda d: (not d.overdue, d.sb_number))
    overdue_count = sum(1 for d in directives if d.overdue)
    if overdue_count:
        state = AdBannerState.RED
        count = overdue_count
    elif directives:
        state = AdBannerState.AMBER
        count = len(directives)
    else:
        state = AdBannerState.GREEN
        count = 0

    return AdStatus(
        engine=engine,
        state=state,
        headline=_headline(state, count, engine.csn),
        overdue_count=overdue_count,
        open_count=len(directives),
        directives=directives,
    )
