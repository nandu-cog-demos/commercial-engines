def _engine_by_serial(client, serial):
    engines = client.get("/api/v1/engines").json()
    return next(e for e in engines if e["serial"] == serial)


def test_health(client):
    assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_list_engines_seeded(client):
    engines = client.get("/api/v1/engines").json()
    serials = {e["serial"] for e in engines}
    assert {"TF9-001234", "TF9-002000", "TF7X-000100"} <= serials
    assert all(e["family"].startswith("TF-") for e in engines)


def test_get_engine_detail(client):
    e = _engine_by_serial(client, "TF9-001234")
    detail = client.get(f"/api/v1/engines/{e['id']}").json()
    assert detail["operatorName"] == "Northwind Air"
    assert detail["csn"] > 0


def test_engine_sb_records(client):
    e = _engine_by_serial(client, "TF9-001234")
    records = client.get(f"/api/v1/engines/{e['id']}/sb-records").json()
    assert len(records) >= 1
    assert {"sbNumber", "status"} <= set(records[0])


def test_list_service_bulletins(client):
    sbs = client.get("/api/v1/service-bulletins").json()
    numbers = {s["sbNumber"] for s in sbs}
    assert "TF9-72-0031" in numbers
    tf9 = client.get("/api/v1/service-bulletins?family=TF-9").json()
    assert all(s["family"] == "TF-9" for s in tf9)


def test_get_service_bulletin(client):
    sbs = client.get("/api/v1/service-bulletins").json()
    sb = client.get(f"/api/v1/service-bulletins/{sbs[0]['id']}").json()
    assert sb["sbNumber"] == sbs[0]["sbNumber"]


def test_list_shop_visits(client):
    visits = client.get("/api/v1/shop-visits").json()
    assert len(visits) >= 1
    assert {"engineSerial", "status", "workscope"} <= set(visits[0])


def test_engine_shop_visits(client):
    e = _engine_by_serial(client, "TF9-001234")
    visits = client.get(f"/api/v1/engines/{e['id']}/shop-visits").json()
    assert all(v["engineSerial"] == "TF9-001234" for v in visits)


def test_release_shop_visit_transitions_to_released(client):
    visits = client.get("/api/v1/shop-visits").json()
    open_visit = next(v for v in visits if v["status"] != "RELEASED")
    resp = client.post(
        f"/api/v1/shop-visits/{open_visit['id']}/release", json={"releasedBy": "qa.tester"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "RELEASED"


def test_release_already_released_conflicts(client):
    visits = client.get("/api/v1/shop-visits").json()
    released = next((v for v in visits if v["status"] == "RELEASED"), None)
    assert released is not None
    resp = client.post(
        f"/api/v1/shop-visits/{released['id']}/release", json={"releasedBy": "qa.tester"}
    )
    assert resp.status_code == 409


def test_get_missing_engine_404(client):
    assert client.get("/api/v1/engines/999999").status_code == 404


# --- NO-196: engine compliance view and mandatory SB release gate ---------------------------

def _compliance(client, serial):
    e = _engine_by_serial(client, serial)
    resp = client.get(f"/api/v1/engines/{e['id']}/compliance")
    assert resp.status_code == 200
    return {r["sbNumber"]: r for r in resp.json()}


def _visit_by_serial(client, serial):
    return next(v for v in client.get("/api/v1/shop-visits").json() if v["engineSerial"] == serial)


def test_bdd_01_ac_01_tf9_001234_two_overdue_mandatory(client):
    rows = _compliance(client, "TF9-001234")
    assert set(rows) == {"TF9-72-0031", "TF9-73-0044"}
    expected_keys = {
        "sbNumber", "title", "category", "status", "complianceStatus",
        "complianceDeadlineCycles", "cyclesRemaining", "overdue", "relatedAdNumber",
    }
    for r in rows.values():
        assert expected_keys <= set(r)
        assert r["category"] == "MANDATORY"
        assert r["status"] == "ACTIVE"
        assert r["complianceStatus"] == "OPEN"
        assert r["overdue"] is True
    assert rows["TF9-72-0031"]["cyclesRemaining"] == -2250
    assert rows["TF9-72-0031"]["complianceDeadlineCycles"] == 12000
    assert rows["TF9-72-0031"]["relatedAdNumber"] == "AD 2025-14-07"
    assert rows["TF9-73-0044"]["cyclesRemaining"] == -1250


def test_bdd_02_ac_02_tf9_002000_one_recommended_no_deadline(client):
    rows = _compliance(client, "TF9-002000")
    assert list(rows) == ["TF9-79-0012"]
    r = rows["TF9-79-0012"]
    assert r["category"] == "RECOMMENDED"
    assert r["complianceDeadlineCycles"] is None
    assert r["cyclesRemaining"] is None
    assert r["overdue"] is False
    assert r["complianceStatus"] == "OPEN"


def test_bdd_03_ac_03_tf7x_000100_nothing_applicable(client):
    assert _compliance(client, "TF7X-000100") == {}


def test_bdd_04_ac_04_tf9_001750_terminated_sb_is_overdue_but_surfaced(client):
    rows = _compliance(client, "TF9-001750")
    assert list(rows) == ["TF9-72-0019"]
    r = rows["TF9-72-0019"]
    assert r["status"] == "TERMINATED"
    assert r["category"] == "MANDATORY"
    assert r["overdue"] is True
    assert r["cyclesRemaining"] == -6020


def test_bdd_05_ac_05_compliance_unknown_engine_404(client):
    assert client.get("/api/v1/engines/999999/compliance").status_code == 404


def test_bdd_06_ac_06_range_parsing_and_applicability():
    from app import models
    from app.compliance import compliance_rows, is_applicable, parse_ranges, serial_suffix

    assert parse_ranges("000500-000900,001200-001300") == [(500, 900), (1200, 1300)]
    assert serial_suffix("TF9-001234") == 1234
    assert serial_suffix("TF7X-000100") == 100

    sb = models.ServiceBulletin(
        sb_number="X", title="x", family="TF-9", category=models.SbCategory.MANDATORY,
        status=models.SbStatus.ACTIVE, applicability_ranges="000500-000900,001200-001300",
        compliance_deadline_cycles=1000, issued_on=None,
    )

    def eng(serial, family="TF-9", csn=500):
        return models.Engine(serial=serial, family=family, operator_code="X",
                             operator_name="X", csn=csn, tsn=0, compliance=[])

    assert is_applicable(sb, eng("TF9-000500"))
    assert is_applicable(sb, eng("TF9-000900"))
    assert not is_applicable(sb, eng("TF9-000499"))
    assert not is_applicable(sb, eng("TF9-000901"))
    assert is_applicable(sb, eng("TF9-001234"))
    assert not is_applicable(sb, eng("TF9-001000"))
    assert not is_applicable(sb, eng("TF7X-000700", family="TF-7X"))

    rows = compliance_rows(eng("TF9-000700", csn=1500), [sb])
    assert len(rows) == 1
    assert rows[0].complianceStatus == models.ComplianceStatus.OPEN
    assert rows[0].cyclesRemaining == -500
    assert rows[0].overdue is True


def test_bdd_07_ac_07_complied_rows_never_overdue(client):
    rows = _compliance(client, "TF9-000812")
    assert set(rows) == {"TF9-73-0044", "TF9-72-0027"}
    assert rows["TF9-73-0044"]["complianceStatus"] == "COMPLIED"
    assert rows["TF9-73-0044"]["cyclesRemaining"] == 3200
    assert rows["TF9-72-0027"]["cyclesRemaining"] is None
    assert all(r["overdue"] is False for r in rows.values())


def test_bdd_08_ac_08_engine_list_overdue_mandatory_count(client):
    counts = {e["serial"]: e["overdueMandatoryCount"] for e in client.get("/api/v1/engines").json()}
    assert counts == {
        "TF9-001234": 2, "TF9-001750": 1, "TF9-002000": 0,
        "TF9-000812": 0, "TF7X-000100": 0, "TF7X-000310": 0,
    }


def test_bdd_09_ac_09_release_blocked_by_overdue_mandatory_sbs(client):
    v = _visit_by_serial(client, "TF9-001234")
    resp = client.post(f"/api/v1/shop-visits/{v['id']}/release", json={"releasedBy": "qa.tester"})
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["message"] == "Release blocked by overdue mandatory SBs"
    assert detail["blockingSbs"] == [
        {"sbNumber": "TF9-72-0031", "title": "HPT stage 1 blade retention pin inspection"},
        {"sbNumber": "TF9-73-0044", "title": "Fuel metering unit seal replacement"},
    ]
    assert client.get(f"/api/v1/shop-visits/{v['id']}").json()["status"] == "IN_WORK"


def test_bdd_10_ac_10_release_with_nothing_applicable_succeeds(client):
    v = _visit_by_serial(client, "TF7X-000100")
    resp = client.post(f"/api/v1/shop-visits/{v['id']}/release", json={"releasedBy": "qa.tester"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "RELEASED"
    assert resp.json()["releasedBy"] == "qa.tester"


def test_bdd_11_ac_11_terminated_sb_does_not_block_release(client):
    from datetime import date

    from app import db as db_module
    from app import models

    e = _engine_by_serial(client, "TF9-001750")
    with db_module.SessionLocal() as s:
        visit = models.ShopVisit(
            engine_id=e["id"], shop="Talon Cincinnati", workscope="Test visit",
            inducted_on=date(2026, 9, 1), status=models.ShopVisitStatus.IN_WORK,
        )
        s.add(visit)
        s.commit()
        visit_id = visit.id

    resp = client.post(f"/api/v1/shop-visits/{visit_id}/release", json={"releasedBy": "qa.tester"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "RELEASED"


def test_bdd_12_ac_12_already_released_still_409(client):
    v = _visit_by_serial(client, "TF9-000812")
    resp = client.post(f"/api/v1/shop-visits/{v['id']}/release", json={"releasedBy": "qa.tester"})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Shop visit already released"
