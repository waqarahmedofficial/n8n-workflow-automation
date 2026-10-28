# Runbook — Invoice Extraction: Table + Exceptions (n8n)

## What it does
Reads every invoice file in a drop folder, extracts **invoice number, date,
vendor, total, currency**, writes clean rows to a table (CSV) and routes
anything incomplete or unreadable to an **exceptions file with the reason
named** — for a human to review. A corrupted file is flagged, it never
crashes the run.

Flow: `Webhook (kickoff) → Config → Read files → Parse → IF valid`
→ valid: table CSV · invalid: exceptions CSV

## How to import
1. In n8n: **Workflows → Import from File**, choose `invoice-extraction.json`.
2. Open **1. Config** and set your folder + output paths (see below).
3. Activate, then POST anything to the webhook URL to start a batch
   (or replace the webhook with a Schedule trigger for hands-off runs).
4. Review the exceptions file after the first run and tune the parser to
   your suppliers' invoice layouts.

## What you (the buyer) must supply
All in the **1. Config** step:
- `invoiceFolder` — where invoice files land (sample: local test folder).
  In production this is typically a synced Drive/Dropbox folder or an
  SFTP drop; swap the Read step's source accordingly.
- `tablePath` / `exceptionsPath` — where the two CSVs are written
  (or replace the write steps with Google Sheets appends on your account).
- `maxFilesPerRun` — batch guard (sample: 500). Files beyond the cap wait
  for the next run, so a huge drop folder cannot flood downstream systems.
- No credentials are stored in the workflow file. The sample parses
  text-based invoices; scanned-image invoices need an OCR/parser service
  connected by you (your account, your key).

## Maintain / extend
- New supplier layout? Add its label variants in the Parse step (the
  accepted labels for number/date/total are listed at the top of the code).
- **Exception routing is the safety net:** anything the parser is unsure
  about lands in exceptions with a named issue (`Missing total amount`,
  `Unreadable/corrupted file content`, …) instead of silently entering
  the books.
- **Rate limits / pagination:** if you extend this to call an OCR or
  accounting API per invoice, process in batches (Loop Over Items + Wait)
  and keep `maxFilesPerRun` set — per-file API calls are the classic way
  to get a key throttled.

## Sample test evidence (this build)
7 files executed on a local n8n instance: 4 clean invoices → table;
3 flagged → exceptions (missing total; missing invoice number + garbled
date; deliberately corrupted binary file, flagged and the run completed
normally). See `evidence/`.
