import pytest

from app.compliance import is_applicable, parse_ranges, serial_in_ranges, serial_suffix
from app.models import Engine, SbCategory, SbStatus, ServiceBulletin


def _engine(serial="TF9-001234", family="TF-9", csn=14250):
    return Engine(serial=serial, family=family, operator_code="NWA", operator_name="Northwind Air",
                  csn=csn, tsn=0, position=None)


def _sb(ranges="001000-001500", family="TF-9", status=SbStatus.ACTIVE):
    return ServiceBulletin(sb_number="TF9-72-0031", title="t", family=family,
                           category=SbCategory.MANDATORY, status=status,
                           applicability_ranges=ranges, compliance_deadline_cycles=12000)


@pytest.mark.parametrize(
    ("serial", "expected"), [("TF9-001234", 1234), ("TF7X-000100", 100), ("TF9-ABC", None)]
)
def test_serial_suffix(serial, expected):
    assert serial_suffix(serial) == expected


def test_parse_ranges_disjoint():
    assert parse_ranges("000500-000900,001200-001300") == [(500, 900), (1200, 1300)]


@pytest.mark.parametrize(
    ("serial", "expected"),
    [
        ("TF9-000500", True),   # first of a range
        ("TF9-000900", True),   # last of a range
        ("TF9-001250", True),   # second, disjoint range
        ("TF9-001000", False),  # between the two ranges
        ("TF9-001400", False),  # past both ranges
    ],
)
def test_serial_in_disjoint_ranges(serial, expected):
    assert serial_in_ranges(serial, "000500-000900,001200-001300") is expected


def test_is_applicable_requires_matching_family():
    assert is_applicable(_engine(family="TF-7X"), _sb()) is False


def test_is_applicable_excludes_terminated_sb():
    assert is_applicable(_engine(), _sb(status=SbStatus.TERMINATED)) is False


def test_is_applicable_serial_outside_all_ranges():
    assert is_applicable(_engine(serial="TF9-001750"), _sb()) is False


def test_is_applicable_happy_path():
    assert is_applicable(_engine(), _sb()) is True
