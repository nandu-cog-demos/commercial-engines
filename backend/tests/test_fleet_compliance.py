from app.compliance import (
    parse_applicability_ranges,
    sb_applies_to_engine,
    serial_suffix,
)
from app.models import Engine, SbCategory, SbStatus, ServiceBulletin


def _engine(serial: str, family: str = "TF-9", csn: int = 10000) -> Engine:
    return Engine(
        serial=serial, family=family, operator_code="NWA", operator_name="Northwind Air",
        csn=csn, tsn=csn * 2, position=None,
    )


def _sb(ranges: str, family: str = "TF-9") -> ServiceBulletin:
    return ServiceBulletin(
        sb_number="TF9-00-0000", title="test", family=family, category=SbCategory.MANDATORY,
        status=SbStatus.ACTIVE, applicability_ranges=ranges, compliance_deadline_cycles=None,
        related_ad_number=None, issued_on=None, summary=None,
    )


def test_parse_applicability_ranges_handles_single_and_disjoint_ranges():
    assert parse_applicability_ranges("001000-001500") == [(1000, 1500)]
    assert parse_applicability_ranges("000500-000900,001200-001300") == [(500, 900), (1200, 1300)]


def test_serial_suffix_strips_family_prefix():
    assert serial_suffix("TF9-001234") == 1234
    assert serial_suffix("TF7X-000100") == 100


def test_applicability_includes_range_boundaries():
    sb = _sb("001000-001500")
    assert sb_applies_to_engine(sb, _engine("TF9-001000")) is True
    assert sb_applies_to_engine(sb, _engine("TF9-001500")) is True
    assert sb_applies_to_engine(sb, _engine("TF9-000999")) is False
    assert sb_applies_to_engine(sb, _engine("TF9-001501")) is False


def test_applicability_matches_any_of_multiple_disjoint_ranges():
    sb = _sb("000500-000900,001200-001300")
    assert sb_applies_to_engine(sb, _engine("TF9-000812")) is True
    assert sb_applies_to_engine(sb, _engine("TF9-001234")) is True
    assert sb_applies_to_engine(sb, _engine("TF9-001000")) is False


def test_applicability_requires_matching_family():
    sb = _sb("000200-000400", family="TF-7X")
    assert sb_applies_to_engine(sb, _engine("TF9-000310", family="TF-9")) is False
    assert sb_applies_to_engine(sb, _engine("TF7X-000310", family="TF-7X")) is True


def _summary(client):
    resp = client.get("/api/v1/fleet/compliance-summary")
    assert resp.status_code == 200
    return resp.json()


def _engine_row(summary, serial):
    return next(
        e for o in summary["operators"] for e in o["engines"] if e["serial"] == serial
    )


def test_fleet_summary_counts_overdue_mandatory_sbs_per_operator(client):
    summary = _summary(client)
    assert summary["engineCount"] == 6
    assert summary["enginesWithOverdueMandatory"] == 1
    assert summary["overdueMandatorySbCount"] == 2

    by_code = {o["operatorCode"]: o for o in summary["operators"]}
    assert set(by_code) == {"NWA", "CCG", "CE"}
    assert by_code["NWA"]["enginesWithOverdueMandatory"] == 1
    assert by_code["NWA"]["overdueMandatorySbCount"] == 2
    assert by_code["CCG"]["overdueMandatorySbCount"] == 0
    assert by_code["CE"]["overdueMandatorySbCount"] == 0


def test_fleet_summary_marks_engine_with_overdue_mandatory_sbs_red(client):
    row = _engine_row(_summary(client), "TF9-001234")
    assert row["ragStatus"] == "RED"
    assert row["overdueMandatoryCount"] == 2
    assert row["applicableSbCount"] == 2
    assert row["operatorName"] == "Northwind Air"


def test_fleet_summary_marks_engine_with_open_non_overdue_sb_amber(client):
    row = _engine_row(_summary(client), "TF9-002000")
    assert row["ragStatus"] == "AMBER"
    assert row["overdueMandatoryCount"] == 0
    assert row["openSbCount"] == 1


def test_fleet_summary_marks_engine_with_no_applicable_sbs_green(client):
    row = _engine_row(_summary(client), "TF7X-000100")
    assert row["ragStatus"] == "GREEN"
    assert row["applicableSbCount"] == 0
    assert row["overdueMandatoryCount"] == 0


def test_fleet_summary_ignores_terminated_mandatory_sb(client):
    row = _engine_row(_summary(client), "TF9-001750")
    assert row["applicableSbCount"] == 1
    assert row["overdueMandatoryCount"] == 0
    assert row["ragStatus"] == "GREEN"


def test_fleet_summary_marks_fully_complied_engine_green(client):
    row = _engine_row(_summary(client), "TF9-000812")
    assert row["ragStatus"] == "GREEN"
    assert row["openSbCount"] == 0
    assert row["overdueMandatoryCount"] == 0
