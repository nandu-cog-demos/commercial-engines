# CES-482 — Engine compliance view and mandatory SB release gate

**Type:** Feature
**Component:** Fleet Compliance Portal
**Priority:** High
**Reporter:** Fleet Support Engineering
**Assignee:** _unassigned_

## Background

The portal already tracks engines, service bulletins (SBs), raw compliance
records, and shop visits. Today a fleet support engineer has to open the SB list
and the per-engine SB records side by side and work out **by hand** which SBs
actually apply to a given engine and which of those are overdue. There is no
consolidated compliance view, and nothing stops a shop from releasing an engine
that still has an overdue mandatory SB open.

We want a first-class compliance view per engine and a release gate on shop
visits.

## Applicability rule

An SB applies to an engine when **both** hold:

1. The SB `family` equals the engine `family`.
2. The numeric suffix of the engine serial falls inside **any** of the SB's
   `applicabilityRanges` (inclusive). Ranges are comma-separated
   `start-end` pairs, e.g. `001000-001500,002200-002400`. The numeric suffix is
   the digits after the family prefix, e.g. `TF9-001234` → `1234`,
   `TF7X-000100` → `100`.

Applicability does **not** consider SB status here; status is surfaced so the UI
and the gate can reason about it (see below).

## Requirements

1. **Endpoint:** `GET /api/v1/engines/{id}/compliance` returns one row per
   **applicable** SB:
   - `sbNumber`, `title`, `category`, `status` (SB status), `complianceStatus`
     (from the engine's record, defaulting to `OPEN` when no record exists),
   - `cyclesRemaining` = `complianceDeadlineCycles - engine.csn`, or `null` when
     the SB has no deadline,
   - `overdue` = `true` when the SB has a deadline, `cyclesRemaining < 0`, and
     the compliance status is not `COMPLIED`,
   - `relatedAdNumber`.
2. **Engine detail:** add a **Compliance** tab. Overdue MANDATORY rows are
   highlighted. The tab shows a red badge with the overdue count.
3. **Release gate:** `POST /api/v1/shop-visits/{id}/release` returns **409** with
   the list of blocking SBs (sbNumber + title) when the visit's engine has any
   applicable SB that is **MANDATORY, compliance status OPEN, and overdue**. The
   UI shows a blocking dialog listing them. On no blockers it releases (**200**)
   as it does today.
4. **No applicable SBs:** engines with nothing applicable return an empty
   compliance list and release normally.

## Notes on status

- A `TERMINATED` (or `SUPERSEDED`) SB must **not** block a release even if it
  would otherwise be overdue and mandatory. Only `ACTIVE` mandatory SBs gate.
  (This is the live-demo negative test — implement it.)

## Acceptance criteria

- **Unit tests:** range parsing; boundary serials (first and last of a range);
  multiple disjoint ranges; wrong family; serial outside all ranges.
- **Integration tests:** compliance endpoint against seed data
  (`TF9-001234` → 2 applicable, both overdue mandatory; `TF9-002000` → 1
  recommended, no deadline; `TF7X-000100` → nothing applicable); release gate
  409 path and 200 path.
- **Playwright/E2E:** open `TF9-001234`, Compliance badge shows **2**, attempt to
  release its open shop visit, dialog lists both blocking SBs. Screenshot
  attached to the PR.
- Existing suite stays green.

## Seed data available (already in the repo)

- `TF9-001234` (CSN 14,250): applicable `TF9-72-0031` (deadline 12,000,
  MANDATORY, OPEN) and `TF9-73-0044` (deadline 13,000, MANDATORY, OPEN) → **both
  overdue**; has an open (`IN_WORK`) shop visit.
- `TF9-002000` (CSN 3,100): applicable `TF9-79-0012` (RECOMMENDED, no deadline,
  OPEN).
- `TF7X-000100` (CSN 22,000): no applicable SB (only `TF7X-75-0003` exists for
  TF-7X, range `000200-000400`; serial suffix `100` is outside it).
- `TF9-001750`: applicable `TF9-72-0019` — MANDATORY and would be overdue, but
  its SB status is `TERMINATED`, so it must **not** block release.
- `TF9-73-0044` has two disjoint ranges (`000500-000900,001200-001300`) for the
  range-parsing test.
- `TF9-001300` (CSN 12,600, added for BFC-1): applicable `TF9-73-0044`
  (deadline 13,000, MANDATORY, OPEN) → **not yet overdue, 400 cycles
  remaining**; `TF9-72-0031` is also applicable (suffix `1300` is inside
  `001000-001500`) but is recorded `COMPLIED` at CSN 11,450, so the engine has
  exactly one open mandatory SB. This is the "due soon" scenario.
