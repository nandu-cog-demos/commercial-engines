"""Seed data for the demo fleet. Idempotent: skips if engines already exist."""

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    ComplianceStatus,
    Engine,
    SbCategory,
    SbCompliance,
    SbStatus,
    ServiceBulletin,
    ShopVisit,
    ShopVisitStatus,
)

ENGINES = [
    dict(serial="TF9-001234", family="TF-9", operator_code="NWA", operator_name="Northwind Air",
         csn=14250, tsn=31880, position="Shop - Talon Cincinnati"),
    dict(serial="TF9-001750", family="TF-9", operator_code="NWA", operator_name="Northwind Air",
         csn=15020, tsn=33410, position="N781NW / #1"),
    dict(serial="TF9-001300", family="TF-9", operator_code="NWA", operator_name="Northwind Air",
         csn=12600, tsn=27400, position="737-8 N738NW / #2"),
    dict(serial="TF9-002000", family="TF-9", operator_code="CCG", operator_name="Cascadia Cargo",
         csn=3100, tsn=7940, position="N204CC / #2"),
    dict(serial="TF9-000812", family="TF-9", operator_code="CCG", operator_name="Cascadia Cargo",
         csn=9800, tsn=22150, position="N201CC / #1"),
    dict(serial="TF7X-000100", family="TF-7X", operator_code="CE",
         operator_name="Commercial Engines", csn=22000, tsn=48770,
         position="Shop - Talon Singapore"),
    dict(serial="TF7X-000310", family="TF-7X", operator_code="CE",
         operator_name="Commercial Engines", csn=8400, tsn=19020, position="SPARE"),
]

SERVICE_BULLETINS = [
    dict(sb_number="TF9-72-0031", title="HPT stage 1 blade retention pin inspection",
         family="TF-9", category=SbCategory.MANDATORY, status=SbStatus.ACTIVE,
         applicability_ranges="001000-001500", compliance_deadline_cycles=12000,
         related_ad_number="AD 2025-14-07", issued_on=date(2025, 6, 2),
         summary="Borescope inspection of retention pins; replace on any indication."),
    dict(sb_number="TF9-73-0044", title="Fuel metering unit seal replacement",
         family="TF-9", category=SbCategory.MANDATORY, status=SbStatus.ACTIVE,
         applicability_ranges="000500-000900,001200-001300", compliance_deadline_cycles=13000,
         related_ad_number="AD 2025-22-03", issued_on=date(2025, 9, 15),
         summary="Replace FMU shaft seal P/N revision B with revision D."),
    dict(sb_number="TF9-79-0012", title="Oil scavenge screen mesh upgrade",
         family="TF-9", category=SbCategory.RECOMMENDED, status=SbStatus.ACTIVE,
         applicability_ranges="001900-002100", compliance_deadline_cycles=None,
         related_ad_number=None, issued_on=date(2026, 1, 20),
         summary="Finer mesh reduces nuisance chip-detector indications."),
    dict(sb_number="TF9-72-0027", title="Fan blade dovetail lubrication interval",
         family="TF-9", category=SbCategory.OPTIONAL, status=SbStatus.ACTIVE,
         applicability_ranges="000800-000900", compliance_deadline_cycles=None,
         related_ad_number=None, issued_on=date(2024, 11, 4),
         summary="Extends dovetail lube interval from 1,500 to 2,000 cycles."),
    dict(sb_number="TF9-72-0019", title="Combustor liner cooling hole rework",
         family="TF-9", category=SbCategory.MANDATORY, status=SbStatus.TERMINATED,
         applicability_ranges="001600-001800", compliance_deadline_cycles=9000,
         related_ad_number="AD 2023-08-11", issued_on=date(2023, 4, 12),
         summary="Terminated 2025-12-01; superseded by liner redesign at next overhaul."),
    dict(sb_number="TF7X-75-0003", title="Bleed valve actuator harness re-route",
         family="TF-7X", category=SbCategory.MANDATORY, status=SbStatus.ACTIVE,
         applicability_ranges="000200-000400", compliance_deadline_cycles=10000,
         related_ad_number="AD 2024-19-02", issued_on=date(2024, 9, 30),
         summary="Harness chafing against the case flange; re-route and add standoff."),
]

# (engine serial, sb number, status, complied date, complied CSN)
COMPLIANCE = [
    ("TF9-001234", "TF9-72-0031", ComplianceStatus.OPEN, None, None),
    ("TF9-001234", "TF9-73-0044", ComplianceStatus.OPEN, None, None),
    ("TF9-001234", "TF9-72-0027", ComplianceStatus.COMPLIED, date(2025, 3, 18), 11900),
    ("TF9-001300", "TF9-73-0044", ComplianceStatus.OPEN, None, None),
    ("TF9-001300", "TF9-72-0031", ComplianceStatus.COMPLIED, date(2025, 11, 6), 11450),
    ("TF9-001750", "TF9-72-0019", ComplianceStatus.OPEN, None, None),
    ("TF9-001750", "TF9-72-0027", ComplianceStatus.COMPLIED, date(2025, 5, 2), 13100),
    ("TF9-002000", "TF9-79-0012", ComplianceStatus.OPEN, None, None),
    ("TF9-002000", "TF9-72-0027", ComplianceStatus.OPEN, None, None),
    ("TF9-000812", "TF9-73-0044", ComplianceStatus.COMPLIED, date(2026, 2, 9), 9400),
    ("TF9-000812", "TF9-72-0027", ComplianceStatus.COMPLIED, date(2025, 1, 27), 7200),
    ("TF7X-000310", "TF7X-75-0003", ComplianceStatus.COMPLIED, date(2025, 7, 14), 6100),
]

SHOP_VISITS = [
    dict(serial="TF9-001234", shop="Talon Cincinnati",
         workscope="Performance restoration, HPT module",
         inducted_on=date(2026, 8, 21), status=ShopVisitStatus.IN_WORK),
    dict(serial="TF7X-000100", shop="Talon Singapore", workscope="Hospital visit, LPT case crack",
         inducted_on=date(2026, 9, 9), status=ShopVisitStatus.INDUCTED),
    dict(serial="TF9-000812", shop="Talon Cincinnati", workscope="Overhaul",
         inducted_on=date(2026, 1, 12), status=ShopVisitStatus.RELEASED,
         released_at=datetime(2026, 3, 3, 16, 42), released_by="r.okafor"),
]


def seed(db: Session) -> None:
    if db.scalar(select(Engine.id).limit(1)) is not None:
        return

    engines = {e["serial"]: Engine(**e) for e in ENGINES}
    sbs = {s["sb_number"]: ServiceBulletin(**s) for s in SERVICE_BULLETINS}
    db.add_all(engines.values())
    db.add_all(sbs.values())
    db.flush()

    for serial, sb_number, status, complied_date, complied_csn in COMPLIANCE:
        db.add(
            SbCompliance(
                engine_id=engines[serial].id,
                sb_id=sbs[sb_number].id,
                status=status,
                complied_date=complied_date,
                complied_at_csn=complied_csn,
            )
        )

    for sv in SHOP_VISITS:
        sv = dict(sv)
        serial = sv.pop("serial")
        db.add(ShopVisit(engine_id=engines[serial].id, **sv))

    db.commit()
