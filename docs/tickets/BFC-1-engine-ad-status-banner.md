# BFC-1 — Engine detail: airworthiness directive status banner

**Type:** Story
**Component:** Fleet Compliance Portal
**Jira:** https://cog-gtm.atlassian.net/browse/BFC-1

## Background

The engine detail page shows serial, operator, position, CSN and TSN, and hides
compliance state behind the _SB Records_ tab. A line planner reviewing an engine
before a shop visit cannot tell whether a mandatory airworthiness directive (AD)
is overdue, nor how the engine's cycle count sits against each AD deadline.

## Applicability

An AD applies to an engine when all of the following hold:

1. The SB `family` equals the engine `family`.
2. The engine serial suffix falls inside any of the SB's `applicabilityRanges`
   (inclusive; comma-separated `start-end` pairs).
3. The SB status is not `TERMINATED`.

An applicable **MANDATORY** SB counts toward the banner while its compliance
status is `OPEN` (no record at all also counts as `OPEN`). It is **overdue**
when its `complianceDeadlineCycles` is at or below the engine CSN
(`cyclesRemaining <= 0`).

## Endpoint

`GET /api/v1/engines/{id}/ad-status`

```json
{
  "engineId": 1,
  "serial": "TF9-001234",
  "csn": 14250,
  "state": "RED",
  "headline": "2 mandatory ADs overdue at CSN 14,250",
  "overdueCount": 2,
  "openCount": 2,
  "directives": [
    {
      "sbNumber": "TF9-72-0031",
      "title": "HPT stage 1 blade retention pin inspection",
      "category": "MANDATORY",
      "complianceStatus": "OPEN",
      "relatedAdNumber": "AD 2025-14-07",
      "deadlineCycles": 12000,
      "cyclesRemaining": -2250,
      "overdue": true
    }
  ]
}
```

- `state` is `RED` when at least one applicable mandatory AD is overdue, `AMBER`
  when one is open but not past its deadline, otherwise `GREEN`.
- Directives are overdue first, then by SB number. `GREEN` returns an empty list.

## Engine detail banner

Rendered above the tab row on every engine, coloured by `state` (`--danger`,
`--warn`, `--ok`). The state is also stated in the headline text, so colour is
never the only signal. Red and amber banners list each open applicable AD with
its SB number, title, and cycles overdue or remaining; green shows no list.

Out of scope: the shop-visit release gate described in
`CES-482-engine-compliance-view-and-release-gate.md`.

## Seed scenarios

- `TF9-001234` (CSN 14,250) → **red**: `TF9-72-0031` 2,250 cycles overdue,
  `TF9-73-0044` 1,250 cycles overdue.
- `TF9-001300` (CSN 12,600, added for this story) → **amber**: `TF9-73-0044`
  open with 400 cycles remaining; `TF9-72-0031` is COMPLIED on this engine.
- `TF9-000812` (CSN 9,800) → **green**: applicable mandatory `TF9-73-0044` is
  COMPLIED.
- `TF9-001750` (CSN 15,020) → **green**: `TF9-72-0019` is OPEN and past its
  deadline but `TERMINATED`, so it never counts.
- `TF9-002000`, `TF7X-000100`, `TF7X-000310` → **green** (nothing applicable and
  mandatory is open).
