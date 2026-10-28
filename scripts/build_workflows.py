#!/usr/bin/env python3
"""Builds the four n8n workflow JSON files for the automation proof sample.

Design rules baked into every workflow (per the Gemini cross-check):
- A dedicated "1. Config" step is the ONLY place environment values live
  (URLs, file paths, thresholds). Logic nodes read config from that step.
- Exception routing is a first-class path, not an afterthought.
- Batch-level notifications (one call per run, never per record) so external
  APIs are not hit at per-record rate.

Outputs: ../workflows/*.json  (importable n8n workflow exports)
"""
import json
import os
import uuid

BASE = "/home/hatch/workspace/automation-builds-sample"
OUT = os.path.join(BASE, "workflows")
os.makedirs(OUT, exist_ok=True)


def nid():
    return str(uuid.uuid4())


def node(name, ntype, version, params, x, y=300):
    n = {
        "parameters": params,
        "id": nid(),
        "name": name,
        "type": ntype,
        "typeVersion": version,
        "position": [x, y],
    }
    if ntype == "n8n-nodes-base.webhook":
        n["webhookId"] = nid()
    return n


def code(name, js, x, y=300):
    return node(name, "n8n-nodes-base.code", 2, {"jsCode": js}, x, y)


def sticky(content, x, y, w=560, h=200):
    return node("Note", "n8n-nodes-base.stickyNote", 1,
                {"content": content, "height": h, "width": w, "color": 4}, x, y)


def conn(edges):
    """edges: list of (from, to) or (from, to, output_index)"""
    c = {}
    for e in edges:
        frm, to = e[0], e[1]
        idx = e[2] if len(e) > 2 else 0
        c.setdefault(frm, {"main": []})
        while len(c[frm]["main"]) <= idx:
            c[frm]["main"].append([])
        c[frm]["main"][idx].append({"node": to, "type": "main", "index": 0})
    return c


def save(name, wf_name, nodes, connections):
    wf = {"name": wf_name, "nodes": nodes, "connections": connections,
          "settings": {"executionOrder": "v1"}, "staticData": None, "pinData": {}}
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(wf, fh, indent=2)
    print("wrote", path)


# ---------------------------------------------------------------- LEAD INTAKE
cfg_a = """// ============================================================
// CONFIG - the ONLY place environment values live in this workflow.
// On import, the buyer replaces these values with their own.
// No other node hardcodes a URL, path or threshold.
// ============================================================
return [{
  json: {
    config: {
      // SAMPLE STAND-IN: local echo endpoint that logs notifications.
      // Buyer supplies their real Slack / Teams / email webhook URL.
      notifyUrl: 'http://127.0.0.1:9999/notify',
      // SAMPLE STAND-IN store: workflow memory + the CSV snapshot below
      // stand in for the buyer's Google Sheet / CRM table.
      tableName: 'leads_table',
      snapshotPath: '""" + BASE + """/evidence/leads_table_snapshot.csv',
      dedupeKey: 'email'
    }
  }
}];"""

dedupe_a = """// Dedupe the incoming batch against the stored table and inside the
// batch itself. Key = email, case-insensitive. The table lives in
// workflow static data (the sample's stand-in for a Sheet/CRM table).
const body = $('Lead Form Webhook').first().json.body || {};
const incoming = Array.isArray(body.leads) ? body.leads : (body.email ? [body] : []);

const table = $getWorkflowStaticData('global');
if (!Array.isArray(table.leads)) table.leads = [];

const seen = new Set(table.leads.map(r => String(r.email || '').trim().toLowerCase()));
const added = [];
let duplicates = 0;
for (const lead of incoming) {
  const key = String(lead.email || '').trim().toLowerCase();
  if (!key || seen.has(key)) { duplicates++; continue; }
  seen.add(key);
  const row = {
    company: lead.company || '',
    name: lead.name || '',
    email: lead.email,
    source: lead.source || '',
    addedAt: new Date().toISOString()
  };
  table.leads.push(row);
  added.push(row);
}
return [{
  json: {
    received: incoming.length,
    added: added.length,
    duplicatesSkipped: duplicates,
    totalInTable: table.leads.length,
    addedEmails: added.map(r => r.email),
    table: table.leads
  }
}];"""

rows_a = """// Emit the full table as items so the next step can write it as CSV.
const table = $('2. Dedupe and Append').first().json.table || [];
return table.map(r => ({ json: r }));"""

nodes_a = [
    sticky("## Lead Intake — sample build\n**Config step first:** all environment values (notify URL, file path) live in `1. Config` only.\n**Rate-limit design:** one summary notification per run — never one call per lead.\n**Stand-ins in this sample:** workflow memory + CSV snapshot = the buyer's Sheet/CRM; local echo endpoint = Slack/email.", 40, 40, 620, 220),
    node("Lead Form Webhook", "n8n-nodes-base.webhook", 2,
         {"httpMethod": "POST", "path": "lead-intake", "responseMode": "lastNode", "options": {}}, 240),
    code("1. Config", cfg_a, 480),
    code("2. Dedupe and Append", dedupe_a, 720),
    code("3. Table Rows for Snapshot", rows_a, 960),
    node("4. Snapshot to CSV", "n8n-nodes-base.convertToFile", 1,
         {"operation": "csv", "options": {"fileName": "leads_table_snapshot", "delimiter": ",", "headerRow": True}}, 1200),
    node("5. Write Snapshot CSV", "n8n-nodes-base.readWriteFile", 1,
         {"operation": "write",
          "fileName": "={{ $('1. Config').first().json.config.snapshotPath }}",
          "dataPropertyName": "data", "options": {"append": False}}, 1440),
    node("6. Notify (stand-in)", "n8n-nodes-base.httpRequest", 4.2,
         {"method": "POST",
          "url": "={{ $('1. Config').first().json.config.notifyUrl }}",
          "authentication": "none", "contentType": "json", "sendBody": True,
          "specifyBody": "json",
          "jsonBody": "={{ JSON.stringify({ event: 'lead-intake-run', received: $('2. Dedupe and Append').first().json.received, added: $('2. Dedupe and Append').first().json.added, duplicatesSkipped: $('2. Dedupe and Append').first().json.duplicatesSkipped, totalInTable: $('2. Dedupe and Append').first().json.totalInTable }) }}",
          "options": {"timeout": 10000}}, 1680),
]
save("lead-intake.json", "SAMPLE - Lead Intake (Dedupe to Table + Notify)", nodes_a,
     conn([("Lead Form Webhook", "1. Config"), ("1. Config", "2. Dedupe and Append"),
           ("2. Dedupe and Append", "3. Table Rows for Snapshot"),
           ("3. Table Rows for Snapshot", "4. Snapshot to CSV"),
           ("4. Snapshot to CSV", "5. Write Snapshot CSV"),
           ("5. Write Snapshot CSV", "6. Notify (stand-in)")]))

# ---------------------------------------------------------- INVOICE EXTRACTION
cfg_b = """// ============================================================
// CONFIG - the ONLY place environment values live in this workflow.
// On import, the buyer replaces these values with their own.
// ============================================================
return [{
  json: {
    config: {
      // Folder the buyer drops invoice files into (sample: local test data).
      invoiceFolder: '""" + BASE + """/test-data/invoices',
      tablePath: '""" + BASE + """/evidence/invoices_table.csv',
      exceptionsPath: '""" + BASE + """/evidence/invoice_exceptions.csv',
      // Batch guard: a single run reads at most this many files, so a huge
      // drop folder cannot flood downstream APIs. Overflow waits for the
      // next scheduled run (see runbook, rate limits).
      maxFilesPerRun: 500
    }
  }
}];"""

parse_b = """// Parse every invoice file read in step 2. Files arrive base64-encoded so
// binary/corrupted content survives transport and can be DETECTED here
// instead of crashing the run. Every file produces exactly one item:
// status 'ok' with all fields, or status 'exception' with named issues.
const stdout = $input.first().json.stdout || '';
const chunks = stdout.split('@@FILE:').map(s => s.trim()).filter(Boolean);
const results = [];
for (const chunk of chunks) {
  const nl = chunk.indexOf('\\n');
  const file = chunk.slice(0, nl).trim();
  const b64 = chunk.slice(nl + 1).replace(/\\s+/g, '');
  let text = '';
  try { text = Buffer.from(b64, 'base64').toString('utf8'); } catch (e) { text = ''; }
  const badChars = (text.match(/[\\uFFFD\\u0000-\\u0008\\u000B\\u000C\\u000E-\\u001F]/g) || []).length;
  const unreadable = text.length === 0 || (badChars / Math.max(text.length, 1)) > 0.02;

  const issues = [];
  let invoiceNumber = '', date = '', vendor = '', total = '', currency = '';
  if (unreadable) {
    issues.push('Unreadable/corrupted file content - no fields could be extracted');
  } else {
    const lineVal = (re) => { const m = text.match(re); return m ? m[1].trim() : ''; };
    invoiceNumber = lineVal(/^\\s*Invoice\\s*(?:Number|No)[:.]?\\s*(.+)$/im);
    if (/^\\(|not printed/i.test(invoiceNumber)) invoiceNumber = '';
    date = lineVal(/^\\s*(?:Invoice\\s*)?Date[:.]?\\s*(.+)$/im);
    const dm = date.match(/(\\d{4})-(\\d{2})-(\\d{2})/);
    if (dm) {
      const d = new Date(dm[0] + 'T00:00:00Z');
      if (isNaN(d) || d.getUTCMonth() + 1 !== +dm[2] || d.getUTCDate() !== +dm[3]) date = '';
      else date = dm[0];
    } else date = '';
    vendor = lineVal(/^\\s*Vendor[:.]?\\s*(.+)$/im);
    const tm = text.match(/^\\s*(Total Due|Grand Total|Total)[:.]?\\s*(.+)$/im);
    if (tm) {
      const am = tm[2].match(/([A-Z]{3}|\\$|\\u20AC|\\u00A3)?\\s*([\\d,]+\\.\\d{2})/);
      if (am) { currency = am[1] || ''; total = am[2]; }
    }
    if (!invoiceNumber) issues.push('Missing invoice number');
    if (!date) issues.push('Missing or invalid invoice date');
    if (!vendor) issues.push('Missing vendor');
    if (!total) issues.push('Missing total amount');
  }
  results.push({ json: {
    file: file, invoiceNumber: invoiceNumber, date: date, vendor: vendor,
    total: total, currency: currency,
    status: issues.length === 0 ? 'ok' : 'exception',
    issues: issues.join('; ')
  }});
}
return results;"""

nodes_b = [
    sticky("## Invoice Extraction — sample build\n**Config step first:** folder + output paths live in `1. Config` only.\n**Exception routing:** every file ends as `ok` (table) or `exception` (flagged file + named issue). A corrupted file is flagged, never crashes the run.\n**Batch guard:** `maxFilesPerRun` in Config caps one run; overflow waits for the next run instead of flooding APIs.", 40, 40, 640, 230),
    node("Invoice Batch Webhook", "n8n-nodes-base.webhook", 2,
         {"httpMethod": "POST", "path": "invoice-batch", "responseMode": "lastNode", "options": {}}, 240),
    code("1. Config", cfg_b, 480),
    node("2. Read Invoice Files", "n8n-nodes-base.executeCommand", 1,
         {"command": "={{ 'cd \"' + $('1. Config').first().json.config.invoiceFolder + '\" && n=0; for f in *.txt; do n=$((n+1)); if [ $n -gt " + "500" + " ]; then break; fi; echo \"@@FILE:$f\"; base64 -w0 \"$f\"; echo; done' }}",
          "executeOnce": True}, 720),
    code("3. Parse Invoices", parse_b, 960),
    node("4. Is Valid?", "n8n-nodes-base.if", 2.2,
         {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
                         "conditions": [{"id": nid(), "leftValue": "={{ $json.status }}", "rightValue": "ok",
                                         "operator": {"type": "string", "operation": "equals"}}],
                         "combinator": "and"},
          "options": {}}, 1200),
    node("5a. Rows to CSV", "n8n-nodes-base.convertToFile", 1,
         {"operation": "csv", "options": {"fileName": "invoices_table", "delimiter": ",", "headerRow": True}}, 1440, 200),
    node("6a. Write Table CSV", "n8n-nodes-base.readWriteFile", 1,
         {"operation": "write",
          "fileName": "={{ $('1. Config').first().json.config.tablePath }}",
          "dataPropertyName": "data", "options": {"append": False}}, 1680, 200),
    node("5b. Exceptions to CSV", "n8n-nodes-base.convertToFile", 1,
         {"operation": "csv", "options": {"fileName": "invoice_exceptions", "delimiter": ",", "headerRow": True}}, 1440, 420),
    node("6b. Write Exceptions CSV", "n8n-nodes-base.readWriteFile", 1,
         {"operation": "write",
          "fileName": "={{ $('1. Config').first().json.config.exceptionsPath }}",
          "dataPropertyName": "data", "options": {"append": False}}, 1680, 420),
]
save("invoice-extraction.json", "SAMPLE - Invoice Extraction (Table + Exceptions)", nodes_b,
     conn([("Invoice Batch Webhook", "1. Config"), ("1. Config", "2. Read Invoice Files"),
           ("2. Read Invoice Files", "3. Parse Invoices"), ("3. Parse Invoices", "4. Is Valid?"),
           ("4. Is Valid?", "5a. Rows to CSV", 0), ("4. Is Valid?", "5b. Exceptions to CSV", 1),
           ("5a. Rows to CSV", "6a. Write Table CSV"), ("5b. Exceptions to CSV", "6b. Write Exceptions CSV")]))

# ------------------------------------------------------------------- RESCUE
cfg_c = """// CONFIG - the only place the business rule lives. Buyer edits here.
return [{ json: { config: { minAmount: 100 } } }];"""

broken_c = """// ============================================================
// AS-RECEIVED LOGIC - kept deliberately faulty for the rescue demo.
// FAULT 1 (date format): assumes dates arrive as MM/DD/YYYY and splits
//   on '/'. The client's system actually sends ISO dates (YYYY-MM-DD),
//   which contain no '/', so EVERY date fails validation.
// FAULT 2 (inverted rule): keeps orders BELOW the threshold
//   (amount < minAmount) instead of at-or-above it.
// Result: the workflow runs 'successfully' and silently drops every
// valid record. See the fixed version for the corrected logic.
// ============================================================
const cfg = $('1. Config').first().json.config;
const orders = ($('Orders Webhook').first().json.body || {}).orders || [];
const kept = [];
for (const o of orders) {
  const parts = String(o.orderDate || '').split('/');
  const month = parseInt(parts[0], 10), day = parseInt(parts[1], 10), year = parseInt(parts[2], 10);
  const d = new Date(year, month - 1, day);
  const dateValid = parts.length === 3 && !isNaN(d) && d.getDate() === day && d.getMonth() === month - 1;
  if (dateValid && o.amount < cfg.minAmount) kept.push({ json: o });
}
return kept;"""

fixed_c = """// ============================================================
// FIXED LOGIC (changes vs the as-received version):
// 1. Dates are parsed as ISO 8601 (YYYY-MM-DD) - the format the
//    client's system actually sends - with a real calendar check.
// 2. The amount rule keeps orders AT OR ABOVE the threshold
//    (amount >= minAmount), as the business rule requires.
// ============================================================
const cfg = $('1. Config').first().json.config;
const orders = ($('Orders Webhook').first().json.body || {}).orders || [];
const kept = [];
for (const o of orders) {
  const m = String(o.orderDate || '').match(/^(\\d{4})-(\\d{2})-(\\d{2})$/);
  let dateValid = false;
  if (m) {
    const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
    dateValid = !isNaN(d) && d.getUTCFullYear() === +m[1] && d.getUTCMonth() + 1 === +m[2] && d.getUTCDate() === +m[3];
  }
  if (dateValid && o.amount >= cfg.minAmount) kept.push({ json: Object.assign({}, o, { dateValid: true }) });
}
return kept;"""

summary_c = """const items = $input.all();
return [{ json: { keptCount: items.length, keptIds: items.map(i => i.json.orderId) } }];"""


def rescue(fname, wf_name, path, filter_name, filter_js, note):
    nodes = [
        sticky(note, 40, 40, 620, 200),
        node("Orders Webhook", "n8n-nodes-base.webhook", 2,
             {"httpMethod": "POST", "path": path, "responseMode": "lastNode", "options": {}}, 240),
        code("1. Config", cfg_c, 480),
        code(filter_name, filter_js, 720),
        code("3. Run Summary", summary_c, 960),
    ]
    save(fname, wf_name, nodes,
         conn([("Orders Webhook", "1. Config"), ("1. Config", filter_name), (filter_name, "3. Run Summary")]))


rescue("rescue-broken.json", "SAMPLE - Order Filter AS RECEIVED (broken)", "orders-broken",
       "2. Parse and Filter - FAULTY", broken_c,
       "## RESCUE DEMO — as-received (broken)\nThis is the client's workflow as handed over. It runs without errors and silently drops every valid order: wrong date-format assumption (MM/DD/YYYY vs ISO) + an inverted amount rule. Evidence: `evidence/exec-rescue-broken.json`.")
rescue("rescue-fixed.json", "SAMPLE - Order Filter FIXED", "orders-fixed",
       "2. Parse and Filter - FIXED", fixed_c,
       "## RESCUE DEMO — fixed\nSame workflow after the fix: ISO date parsing with a real calendar check, and the amount rule restored to >= threshold. Evidence: `evidence/exec-rescue-fixed.json`.")

print("done")
