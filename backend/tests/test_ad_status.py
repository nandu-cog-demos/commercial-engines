from app.ad_status import serial_in_ranges, serial_suffix


def _engine_by_serial(client, serial):
    engines = client.get("/api/v1/engines").json()
    return next(e for e in engines if e["serial"] == serial)


def _ad_status(client, serial):
    e = _engine_by_serial(client, serial)
    resp = client.get(f"/api/v1/engines/{e['id']}/ad-status")
    assert resp.status_code == 200
    return resp.json()


def test_serial_suffix_strips_family_prefix():
    assert serial_suffix("TF9-001234") == 1234
    assert serial_suffix("TF7X-000100") == 100
    assert serial_suffix("TF9-ABC") is None


def test_serial_in_ranges_matches_boundaries_and_disjoint_ranges():
    ranges = "000500-000900,001200-001300"
    assert serial_in_ranges("TF9-000500", ranges)
    assert serial_in_ranges("TF9-000900", ranges)
    assert serial_in_ranges("TF9-001300", ranges)
    assert not serial_in_ranges("TF9-001000", ranges)
    assert not serial_in_ranges("TF9-001301", ranges)


def test_ad_status_is_red_when_mandatory_ads_are_overdue(client):
    status = _ad_status(client, "TF9-001234")
    assert status["state"] == "RED"
    assert status["overdueCount"] == 2
    assert status["headline"] == "2 mandatory ADs overdue at CSN 14,250"
    assert [d["sbNumber"] for d in status["directives"]] == ["TF9-72-0031", "TF9-73-0044"]
    assert [d["cyclesRemaining"] for d in status["directives"]] == [-2250, -1250]
    assert all(d["overdue"] for d in status["directives"])


def test_ad_status_is_amber_when_mandatory_ad_is_open_before_its_deadline(client):
    status = _ad_status(client, "TF9-001300")
    assert status["state"] == "AMBER"
    assert status["overdueCount"] == 0
    assert status["openCount"] == 1
    assert status["headline"] == "1 mandatory AD open, none overdue at CSN 12,600"
    assert status["directives"] == [
        {
            "sbNumber": "TF9-73-0044",
            "title": "Fuel metering unit seal replacement",
            "category": "MANDATORY",
            "complianceStatus": "OPEN",
            "relatedAdNumber": "AD 2025-22-03",
            "deadlineCycles": 13000,
            "cyclesRemaining": 400,
            "overdue": False,
        }
    ]


def test_ad_status_is_green_when_every_applicable_mandatory_ad_is_complied(client):
    status = _ad_status(client, "TF9-000812")
    assert status["state"] == "GREEN"
    assert status["directives"] == []
    assert status["headline"] == "No mandatory AD open at CSN 9,800"


def test_terminated_sb_never_counts_toward_the_banner(client):
    status = _ad_status(client, "TF9-001750")
    assert status["state"] == "GREEN"
    assert status["directives"] == []


def test_ad_status_ignores_non_mandatory_and_out_of_range_bulletins(client):
    recommended_only = _ad_status(client, "TF9-002000")
    assert recommended_only["state"] == "GREEN"

    wrong_range = _ad_status(client, "TF7X-000100")
    assert wrong_range["state"] == "GREEN"
    assert wrong_range["directives"] == []


def test_ad_status_for_missing_engine_404(client):
    assert client.get("/api/v1/engines/999999/ad-status").status_code == 404
