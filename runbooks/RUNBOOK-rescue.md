# Runbook — Workflow Rescue Demo: Order Filter (n8n)

## The situation
A client's order-filter workflow "ran fine" every day — green executions,
no errors — yet **zero orders ever came out of it**. This package contains
the workflow exactly as received (`rescue-broken.json`), the fixed version
(`rescue-fixed.json`), and the execution records for both.

**Intended rule:** keep orders with amount **≥ 100** and a valid order date.
Test batch: 6 orders → correct result is **3 kept** (150, 200, 320).

## What was wrong (two faults)
1. **Wrong date-format assumption.** The filter parsed dates as
   `MM/DD/YYYY` by splitting on `/`. The client's system actually sends
   ISO dates (`YYYY-MM-DD`), which contain no `/` — so *every* date
   failed validation and every record was discarded.
2. **Inverted amount rule.** The comparison kept orders **below** the
   threshold (`amount < 100`) instead of at-or-above it. Even with
   correct dates, it would have kept exactly the wrong orders.

Individually each fault is a one-line mistake; together they produced a
workflow that looked healthy while silently dropping 100% of valid work.
That is the most expensive class of automation failure, and it is only
visible if someone reconciles input vs output counts.

## The fix
- Parse dates as ISO 8601 with a real calendar check (rejects
  `2026-13-40`-style impossibilities, not just wrong shapes).
- Restore the rule to `amount >= minAmount`, with the threshold in the
  **Config** step (the only place the business rule lives — no hunting
  through nodes to change it).

## Evidence (executed on a local n8n instance)
- As received: 6 orders in → **0 kept**. (`evidence/exec-rescue-broken-*`)
- Fixed: 6 orders in → **3 kept** (ORD-1001, ORD-1003, ORD-1005).
  (`evidence/exec-rescue-fixed-*`)

## How to use / maintain
1. Import either file (**Workflows → Import from File**), activate, POST
   the order batch to its webhook.
2. Change the threshold only in **1. Config**.
3. Standing advice for any rescued workflow: add a run summary like the
   one in this build (in/out counts on every run) so a silent drop is
   visible the same day, not at month-end.
