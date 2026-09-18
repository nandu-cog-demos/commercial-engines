# NO-196 — Engine compliance view and mandatory SB release gate (SDD spec)

**Jira:** https://cog-gtm.atlassian.net/browse/NO-196
**Source ticket:** `docs/tickets/CES-482-engine-compliance-view-and-release-gate.md`
**Branch:** `devin/NO-196-engine-compliance-release-gate`

## Story

As a fleet support engineer I want to open an engine and see which service
bulletins actually apply to it and which are overdue, and I want the shop to be
unable to release an engine that still has an overdue **active mandatory** SB,
so that I stop reconciling SB lists by hand and no non-compliant engine leaves
the shop.

### Decisions taken in the interview

| # | Decision |
|---|---|
| 1 | Shop Visits page gains a **Release** button on non-`RELEASED` rows; it prompts for `releasedBy` and shows a blocking dialog listing the SBs on 409. |
| 2 | Engine list badge counts overdue **MANDATORY** SBs regardless of SB status (so `TF9-001750` shows badge `1` but is still releasable). |
| 3 | Compliance tab badge counts **all** overdue rows. |
| 4 | 409 body: `{"detail": {"message": "Release blocked by overdue mandatory SBs", "blockingSbs": [{"sbNumber", "title"}]}}`. |
| 5 | `GET /api/v1/engines` rows gain `overdueMandatoryCount`; no per-row compliance call. |
| 6 | A small Playwright E2E suite (`frontend/e2e/`) is added; full E2E coverage not required. It is **not** wired into CI. |

### Rules

- **Applicable(SB, engine)** = `sb.family == engine.family` AND
  `suffix(engine.serial) ∈ any range in sb.applicabilityRanges` (inclusive).
  `suffix("TF9-001234") = 1234`, `suffix("TF7X-000100") = 100`.
  SB status is **not** part of applicability.
- **complianceStatus** = the engine's `SbCompliance` record status, else `OPEN`.
- **cyclesRemaining** = `complianceDeadlineCycles - engine.csn`, `null` when no deadline.
- **overdue** = deadline exists AND `cyclesRemaining < 0` AND `complianceStatus != COMPLIED`.
- **blocking(row)** = `overdue` AND `category == MANDATORY` AND `status == ACTIVE`
  AND `complianceStatus == OPEN`.
- **overdueMandatoryCount(engine)** = count of rows with `overdue AND category == MANDATORY` (any SB status).

## AC matrix

| AC-ID | Category | Given | When | Then | Verification |
|---|---|---|---|---|---|
| AC-01 | API | Seeded DB; engine `TF9-001234` (CSN 14,250) | `GET /api/v1/engines/{id}/compliance` | 200; exactly 2 rows `TF9-72-0031` and `TF9-73-0044`; each has `sbNumber,title,category,status,complianceStatus,complianceDeadlineCycles,cyclesRemaining,overdue,relatedAdNumber`; both `overdue=true`, `complianceStatus=OPEN`, `cyclesRemaining` -2250 / -1250 | BDD-01, curl |
| AC-02 | API | Engine `TF9-002000` (CSN 3,100) | `GET .../compliance` | 1 row `TF9-79-0012`, `category=RECOMMENDED`, `cyclesRemaining=null`, `overdue=false` | BDD-02 |
| AC-03 | API | Engine `TF7X-000100` (suffix 100, only SB range 000200-000400) | `GET .../compliance` | `[]` | BDD-03 |
| AC-04 | API | Engine `TF9-001750`; SB `TF9-72-0019` MANDATORY/TERMINATED, deadline 9,000, CSN 15,020 | `GET .../compliance` | 1 row, `status=TERMINATED`, `overdue=true` | BDD-04 |
| AC-05 | API | Unknown engine id | `GET /api/v1/engines/999999/compliance` | 404 `Engine not found` | BDD-05 |
| AC-06 | FUNC | Applicability helper | called with boundary serials (first/last of range), disjoint ranges `000500-000900,001200-001300`, wrong family, serial outside ranges | inclusive boundaries match; suffix 1234 matches 2nd range, 1000 does not; wrong family never matches | BDD-06 (unit tests) |
| AC-07 | DATA | Engine `TF9-000812` (CSN 9,800) with COMPLIED records for `TF9-73-0044` and `TF9-72-0027` | `GET .../compliance` | both rows `complianceStatus=COMPLIED`, `overdue=false`; a COMPLIED row is never overdue. Default `OPEN` when no record exists is covered by the BDD-06 unit test | BDD-07 |
| AC-08 | API | `GET /api/v1/engines` | list | each row has `overdueMandatoryCount`; `TF9-001234`=2, `TF9-001750`=1, `TF9-002000`=0, `TF7X-000100`=0, `TF9-000812`=0, `TF7X-000310`=0 | BDD-08 |
| AC-09 | API | Shop visit of `TF9-001234` (IN_WORK) | `POST /api/v1/shop-visits/{id}/release {"releasedBy":"qa"}` | 409; `detail.blockingSbs` = `[TF9-72-0031, TF9-73-0044]` with titles; visit stays `IN_WORK` | BDD-09 |
| AC-10 | API | Shop visit of `TF7X-000100` (INDUCTED, nothing applicable) | release | 200, `status=RELEASED`, `releasedBy` echoed | BDD-10 |
| AC-11 | API | Engine `TF9-001750` (overdue but TERMINATED mandatory SB) with a shop visit | release | 200 — terminated SB never blocks | BDD-11 |
| AC-12 | API | Already-released visit (`TF9-000812`) | release | 409 `Shop visit already released` (unchanged) | BDD-12 |
| AC-13 | UI | Engine detail `TF9-001234` | click **Compliance** tab | table with columns SB / Title / Category / SB Status / Compliance / Deadline / Cycles Remaining / AD; 2 rows; both rows visually flagged (red `overdue` row style + "OVERDUE" chip); tab label shows red badge `2` | BDD-13 |
| AC-14 | UI | Engine detail `TF7X-000100` → Compliance | view | empty-state text "No applicable service bulletins" and no badge | BDD-14 |
| AC-15 | UI | Engines list | view | `TF9-001234` shows red badge `2 overdue`; `TF9-001750` shows `1 overdue`; other rows show no badge | BDD-15 |
| AC-16 | UI | Shop Visits page, row `TF9-001234` IN_WORK | click **Release**, enter name | dialog "Release blocked" listing `TF9-72-0031` and `TF9-73-0044` with titles; status still IN_WORK | BDD-16 |
| AC-17 | UI | Shop Visits page, row `TF7X-000100` INDUCTED | click **Release**, enter name | row becomes RELEASED with releasedBy · date; button disappears | BDD-17 |
| AC-18 | TEST | Backend | `pytest -q` | all new tests named by BDD id pass; existing 11 pass | CI |
| AC-19 | TEST | Frontend | `npm run build` | tsc + vite clean | CI |
| AC-20 | TEST | Playwright | `npm run e2e` (from `frontend/`) | spec passes: badge 2 on `TF9-001234`, Compliance tab rows, blocked release dialog, `TF7X-000100` releasable; runs against a throw-away SQLite DB | BDD-20 |
| AC-21 | UI | Existing pages | walk Engines → detail tabs → Service Bulletins → Shop Visits | no regressions, console error-free | BDD-21 |

## BDD scenarios

**BDD-01 (AC-01)** Given the seeded backend, When `curl localhost:8000/api/v1/engines/1/compliance` (id of `TF9-001234`), Then the JSON is a 2-element list; `TF9-72-0031` → `category=MANDATORY, status=ACTIVE, complianceStatus=OPEN, complianceDeadlineCycles=12000, cyclesRemaining=-2250, overdue=true, relatedAdNumber="AD 2025-14-07"`; `TF9-73-0044` → `cyclesRemaining=-1250, overdue=true`.

**BDD-02 (AC-02)** Given `TF9-002000`, When GET compliance, Then one row `TF9-79-0012` with `category=RECOMMENDED, complianceDeadlineCycles=null, cyclesRemaining=null, overdue=false, complianceStatus=OPEN`.

**BDD-03 (AC-03)** Given `TF7X-000100`, When GET compliance, Then `[]`.

**BDD-04 (AC-04)** Given `TF9-001750`, When GET compliance, Then one row `TF9-72-0019` with `status=TERMINATED, category=MANDATORY, overdue=true, cyclesRemaining=-6020`.

**BDD-05 (AC-05)** When GET `/api/v1/engines/999999/compliance`, Then 404.

**BDD-06 (AC-06)** Unit tests on `app.compliance.serial_suffix` / `parse_ranges` / `is_applicable`:
- `"000500-000900,001200-001300"` → `[(500,900),(1200,1300)]`;
- suffix 500 and 900 applicable (boundaries), 499 and 901 not, 1234 applicable via 2nd range, 1000 not;
- SB family `TF-7X` vs engine `TF-9` with suffix in range → not applicable;
- `serial_suffix("TF7X-000100") == 100`.
- `compliance_rows` for an engine with an applicable SB and no record → `complianceStatus == OPEN`.

**BDD-07 (AC-07)** Given `TF9-000812` (CSN 9,800), When GET compliance, Then rows `TF9-73-0044` (COMPLIED, overdue=false, cyclesRemaining=3200) and `TF9-72-0027` (COMPLIED, cyclesRemaining=null); no row is overdue.

**BDD-08 (AC-08)** When `curl localhost:8000/api/v1/engines`, Then `overdueMandatoryCount` is 2 for `TF9-001234`, 1 for `TF9-001750`, 0 for the other four.

**BDD-09 (AC-09)** Given the IN_WORK shop visit of `TF9-001234`, When `POST .../release {"releasedBy":"qa.tester"}`, Then 409 and `detail.blockingSbs == [{"sbNumber":"TF9-72-0031","title":"HPT stage 1 blade retention pin inspection"},{"sbNumber":"TF9-73-0044","title":"Fuel metering unit seal replacement"}]`; GET the visit → still `IN_WORK`.

**BDD-10 (AC-10)** Given the INDUCTED visit of `TF7X-000100`, When release, Then 200 and `status=RELEASED, releasedBy="qa.tester"`.

**BDD-11 (AC-11)** Given a shop visit created in the test DB for `TF9-001750` (seed has none), When release, Then 200 (terminated SB does not block).

**BDD-12 (AC-12)** Given the RELEASED visit of `TF9-000812`, When release, Then 409 `detail == "Shop visit already released"`.

**BDD-13 (AC-13)** Given browser at `/engines/1`, When clicking tab **Compliance**, Then the tab button shows badge `2`; the table lists `TF9-72-0031` and `TF9-73-0044` with `MANDATORY`, `ACTIVE`, `OPEN`, deadlines 12,000 / 13,000, cycles remaining −2,250 / −1,250, an `OVERDUE` chip; rows have the `overdue` highlight class.

**BDD-14 (AC-14)** Given `/engines/5` (`TF7X-000100`), When clicking **Compliance**, Then text "No applicable service bulletins" and no badge on the tab.

**BDD-15 (AC-15)** Given `/engines`, Then row `TF9-001234` shows a red `2 overdue` badge, `TF9-001750` shows `1 overdue`, `TF9-002000`, `TF9-000812`, `TF7X-000100`, `TF7X-000310` show none.

**BDD-16 (AC-16)** Given `/shop-visits`, When clicking **Release** on the `TF9-001234` IN_WORK row and entering `qa.tester`, Then a "Release blocked" dialog lists `TF9-72-0031 — HPT stage 1 blade retention pin inspection` and `TF9-73-0044 — Fuel metering unit seal replacement`; closing it leaves the row `IN_WORK`.

**BDD-17 (AC-17)** Given `/shop-visits`, When clicking **Release** on the `TF7X-000100` INDUCTED row and entering `qa.tester`, Then the row shows `RELEASED` and `qa.tester · <today>`; the Release button is gone.

**BDD-20 (AC-20)** `cd frontend && npm run e2e` boots backend (`DATABASE_URL=sqlite:///./e2e.db`, fresh) + vite via Playwright `webServer`, runs `e2e/compliance.spec.ts` (BDD-13, BDD-15, BDD-16, BDD-17), exits 0.

**BDD-21 (AC-21)** Walk Engines → `TF9-001234` Overview / SB Records / Shop Visits → Service Bulletins → Shop Visits; all render as before; DevTools console has no errors.

## Traceability

| AC | BDD |
|---|---|
| AC-01 | BDD-01 |
| AC-02 | BDD-02 |
| AC-03 | BDD-03 |
| AC-04 | BDD-04 |
| AC-05 | BDD-05 |
| AC-06 | BDD-06 |
| AC-07 | BDD-07 |
| AC-08 | BDD-08 |
| AC-09 | BDD-09 |
| AC-10 | BDD-10 |
| AC-11 | BDD-11 |
| AC-12 | BDD-12 |
| AC-13 | BDD-13 |
| AC-14 | BDD-14 |
| AC-15 | BDD-15 |
| AC-16 | BDD-16 |
| AC-17 | BDD-17 |
| AC-18 | pytest run |
| AC-19 | npm run build |
| AC-20 | BDD-20 |
| AC-21 | BDD-21 |

## Reuse vs. add

- **Reuse:** `models.py` entities/enums (no schema change), `ApiModel` camelCase pattern, `_engine_or_404` / `_shop_visit_or_404`, `useApi`, tab/table/`.chip`/`.cat-*` styles, `ApiError.body` for the 409 payload, `conftest.py` `client` fixture, seed data unchanged.
- **Add:** `backend/app/compliance.py` (`serial_suffix`, `parse_ranges`, `is_applicable`, `compliance_rows`, `blocking_sbs`), `EngineComplianceRow` + `BlockingSb` schemas, `overdueMandatoryCount` on `EngineOut`, `GET /engines/{id}/compliance`, gate in `release_shop_visit`, `api.engineCompliance`, `EngineComplianceRow` type, Compliance tab, list badge, Release button + dialog, `.badge`/`.overdue` CSS, `frontend/e2e/compliance.spec.ts` + `playwright.config.ts` + `@playwright/test` devDependency.
