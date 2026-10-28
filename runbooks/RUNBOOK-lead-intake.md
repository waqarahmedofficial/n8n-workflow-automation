# Runbook — Lead Intake: Dedupe to Table + Notify (n8n)

## What it does
Receives lead records at a webhook (the shape a web form, Typeform, or a CRM
"send to webhook" action produces), removes duplicates, stores the clean
leads in a table, and sends ONE summary notification per run.

Flow: `Webhook → Config → Dedupe & Append → Table snapshot (CSV) → Notify`

- Duplicates are matched on **email, case-insensitive**, both against the
  stored table and inside the incoming batch itself.
- The notification is a single summary (`received / added / duplicates
  skipped / total in table`) — never one message per lead.

## How to import
1. In n8n: **Workflows → Import from File**, choose `lead-intake.json`.
2. Open the **1. Config** step and replace the sample values (see below).
3. Activate the workflow. The production webhook URL is shown on the
   **Lead Form Webhook** node — point your form/CRM at it.
4. Send one test batch and check the table + notification before going live.

## What you (the buyer) must supply
Everything environment-specific lives in the **1. Config** step only:
- `notifyUrl` — your Slack / Teams / email webhook URL
  (sample value is a local test endpoint).
- The table store: the sample keeps the table in workflow memory and
  writes a CSV snapshot (`snapshotPath`). In production, swap the snapshot
  step for a Google Sheets / Airtable / CRM append step using **your**
  account credentials — no credentials are stored in the workflow file.
- The form/CRM that will POST lead JSON: `{ "leads": [ {company, name,
  email, source}, ... ] }` (a single lead object also works).

## Maintain / extend
- Change the dedupe key in Config + the Dedupe step (e.g. email+company).
- Add enrichment (a lookup step) after Dedupe — it only runs for genuinely
  new leads, which keeps third-party API usage minimal.
- **Rate limits:** the design already batches (one notification per run).
  If you add per-lead external API calls, wrap them in n8n's
  *Loop Over Items* with a 1s Wait, or the provider may throttle/ban the key.

## Sample test evidence (this build)
Two batches were executed against a local n8n instance: batch 1 of 8 leads
contained 2 duplicates (6 added); batch 2 of 5 leads contained 3 already in
the table (2 added). Final table: 8 unique leads. See `evidence/`.
