# n8n Workflow Automation — Builds, Fixes & Handovers

**Working n8n workflows that take repetitive data work off your team — built, executed and evidenced, not just diagrammed.**

Built by **Waqar Ahmed**, spreadsheet & data specialist (7+ years: data cleaning, automation, reconciliation, dashboards and reporting for businesses and agencies).

## Who this is for

Agencies and operations teams who run (or want to run) n8n and need someone to build the unglamorous, high-volume workflows properly: lead intake with deduplication, document/invoice data extraction with exception handling, and diagnosis of workflows that silently drop data.

## What the proof in this repo shows

These are not screenshots of a plan. Each workflow below was built in a real local **n8n v1.116.2** instance, imported, activated and **executed live via production webhooks** against realistic test data. The full n8n execution records are in `evidence/` — all runs finished with status "success".

| Workflow | Test input | Verified result |
|---|---|---|
| **Lead intake** (`workflows/lead-intake.json`) | Batch 1: 8 leads · Batch 2: 5 leads | Batch 1 → 6 added, 2 duplicates skipped. Batch 2 → 2 added, 3 duplicates skipped. Final table: **8 unique leads**. Dedupe works against the stored table *and* inside a batch, case-insensitive on email. One summary notification per run, logged in `evidence/notifications.log`. |
| **Invoice extraction** (`workflows/invoice-extraction.json`) | 7 invoice files | **4 clean rows** extracted (numbers, dates, vendors, totals, currencies — including EUR) and **3 exceptions** correctly flagged with named reasons: missing total; missing invoice number + invalid date; a deliberately corrupted file flagged "unreadable/corrupted" while the run still completed gracefully instead of crashing. |
| **Rescue demo** (`workflows/rescue-broken.json` → `rescue-fixed.json`) | 6 orders | The broken version silently kept **0 of 6** orders (an MM/DD/YYYY date-parse assumption against ISO dates, plus an inverted amount rule — the exact kind of fault that loses data quietly). The fixed version keeps exactly the right **3 orders** (ORD-1001, ORD-1003, ORD-1005). |

Also included: a one-page runbook per workflow (`runbooks/`), the test data used (`test-data/`), the result tables (`evidence/*.csv`), and the reproducible build/proof scripts (`scripts/`).

**Honest scope notes** (the same ones I give clients):
- In this proof, a local table + CSV snapshots stand in for a live Google Sheets/CRM, and a local endpoint stands in for Slack/email notifications. n8n itself, the workflow logic, dedupe, parsing, exception routing and webhook execution are 100% real.
- **Make.com is not offered and not claimed** — these are n8n builds, proven on n8n only.
- First engagements are sold as builds + workflow handover. Rescue of a live third-party account is taken on only after a paid diagnostic.

## What you receive on a real engagement

- The workflow export JSON(s), ready to import into your n8n instance
- A one-page runbook per workflow: what it does, how to import it, exactly which credentials/connections you supply, and how to maintain it
- A single Config step holding all environment values — no hardcoded folder IDs, keys or emails buried inside nodes
- Exception routing as standard: bad records are flagged with reasons, never silently dropped
- Test run evidence on sample data before handover

## How the work runs

1. **Brief in writing** — you describe the process and share sample input files (no live account access needed to start).
2. **Build** — I build the workflow in n8n against your sample data, with dedupe and exception handling.
3. **Proof run** — you see the execution results and output tables before anything touches your live systems.
4. **Handover** — export JSON + runbook; you import it into your instance with your own credentials.
5. **Support window** — fixes and small adjustments after handover, agreed in writing.

## Tools

n8n (self-hosted or cloud) · Webhooks · Google Sheets / CSV data stores · JSON · Python (test harnesses)

## About this sample

This is a **proof-of-capability sample**, built on synthetic test data only — no client data is used or shown. The numbers above come from the execution records committed in `evidence/`, and you can re-run the proof yourself with the scripts in `scripts/`.

## Work with me

I take on freelance projects through Contra: **https://contra.com/mr_world_z7lsrx86**

Communication is **written-only** (chat/email) — clear briefs, documented handovers, no calls needed. Payment via Payoneer or bank transfer.
