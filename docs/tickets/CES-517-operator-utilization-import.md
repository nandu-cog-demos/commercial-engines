# CES-517 — Monthly operator utilization import

**Type:** Story
**Component:** Fleet Compliance Portal
**Priority:** Medium
**Reporter:** D. Marchetti (Fleet Support, NWA/CCG accounts)
**Assignee:** _unassigned_
**Sprint:** FSP 2026-Q4 S2

## Story

As a fleet support engineer, I want to load the monthly utilization report an
operator sends us (cycles and hours per engine serial) into the portal, so that
engine CSN/TSN are current without me editing rows by hand and SB deadlines are
computed against real numbers.

## Context

Every operator sends a utilization file at month end — Northwind's comes out of
their M&E system as a CSV, Cascadia's is an Excel export someone saves as CSV.
Today Priya pastes the numbers into the engines table one at a time. Last month
two TF-9s were missed and `TF9-001750` went a full cycle-count period with a
stale CSN, which is how the 72-0031 deadline slipped past unnoticed.

## What we need

- Upload the operator's file and have the portal apply the new CSN/TSN to the
  matching engines.
- Show me what's going to change before it changes.
- Don't let a bad file wreck the fleet table — a typo shouldn't make an engine
  go backwards in cycles.
- Some record that the import happened, who did it and from which file.

## Out of scope

- Reading Excel directly; operators will export to CSV.
- Automatic pickup from email/SFTP (separate ticket, CES-533).

## Notes

Sample from Northwind's last file (header row is theirs):

```
ESN,Cycles,Hours,Report Date
TF9-001234,14312,32004,2026-09-30
TF9-001750,15118,33602,2026-09-30
```

Cascadia's has the same columns but calls them `Serial Number,CSN,TSN,As Of`.
