#!/usr/bin/env python3
"""Proof driver for the automation-builds sample.

Talks to the locally running n8n instance over its REST API:
  1. creates a throwaway LOCAL owner login (localhost instance only -
     not an external account) so the REST API can be used,
  2. imports the four sample workflows and activates them,
  3. fires the real test payloads at the production webhooks,
  4. downloads the full execution records as evidence files,
  5. prints a per-workflow count summary.

Idempotent: on re-run it reuses workflows whose names already exist.
Usage: python3 run_proof.py
"""
import json
import os
import time
import urllib.request
import urllib.error
import http.cookiejar

BASE = "http://127.0.0.1:5678"
ROOT = "/home/hatch/workspace/automation-builds-sample"
OWNER = {"email": "sample.owner@example.com", "firstName": "Sample", "lastName": "Owner",
         "password": "LocalSample#2026"}

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def call(method, path, payload=None, raw_headers=None):
    url = BASE + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")

    def parse(text):
        try:
            return json.loads(text) if text else {}
        except Exception:
            return {"raw": text[:400]}

    try:
        with opener.open(req, timeout=60) as resp:
            return resp.status, parse(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, parse(e.read().decode("utf-8", "replace"))


def wait_ready(tries=60):
    for _ in range(tries):
        try:
            with urllib.request.urlopen(BASE + "/healthz", timeout=5) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(2)
    return False


def ensure_login():
    # NOTE: n8n 1.116 has no GET /rest/me route ("Cannot GET /rest/me").
    # A 200 from owner/setup or login IS the session proof (it sets the
    # auth cookie); we verify by listing workflows with the session.
    def session_works():
        s, _b = call("GET", "/rest/workflows")
        return s == 200

    last = None
    for _ in range(30):
        if session_works():
            print("session active for", OWNER["email"])
            return
        s2, b2 = call("POST", "/rest/owner/setup", OWNER)
        if s2 in (200, 201):
            last = (s2, "owner setup ok")
        else:
            s3, b3 = call("POST", "/rest/login",
                          {"emailOrLdapLoginId": OWNER["email"], "password": OWNER["password"]})
            last = (s3, b3 if s3 != 200 else "login ok")
        time.sleep(2)
    raise AssertionError(f"login failed after retries: {last}")


def as_list(body):
    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        for key in ("data", "results", "workflows"):
            v = body.get(key)
            if isinstance(v, list):
                return v
            if isinstance(v, dict):
                inner = as_list(v)
                if inner:
                    return inner
    return []


def find_workflow(name):
    status, body = call("GET", "/rest/workflows")
    for wf in as_list(body):
        if isinstance(wf, dict) and wf.get("name") == name:
            return wf.get("id")
    return None


def import_workflow(filename):
    with open(os.path.join(ROOT, "workflows", filename), encoding="utf-8") as fh:
        wf = json.load(fh)
    existing = find_workflow(wf["name"])
    if existing:
        print("reuse workflow", wf["name"], existing)
        return existing
    payload = {"name": wf["name"], "nodes": wf["nodes"], "connections": wf["connections"],
               "settings": wf.get("settings", {}), "staticData": None, "active": False}
    status, body = call("POST", "/rest/workflows", payload)
    print("create response:", status, json.dumps(body)[:800])
    assert status in (200, 201), f"create {filename} failed: {status} {json.dumps(body)[:600]}"
    data = body.get("data", body)
    wf_id = data["id"]
    print("created workflow", wf["name"], wf_id)
    return wf_id


def activate(wf_id):
    status, body = call("POST", f"/rest/workflows/{wf_id}/activate")
    if status not in (200, 201):
        status, body = call("PATCH", f"/rest/workflows/{wf_id}", {"active": True})
    print("activate", wf_id, "->", status)


def post_webhook(path, payload):
    req = urllib.request.Request(BASE + "/webhook/" + path,
                                 data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read().decode("utf-8", "replace")[:500]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:500]


def fetch_executions(wf_id, tag):
    time.sleep(2)
    status, body = call("GET", f"/rest/executions?filter={urllib.parse.quote(json.dumps({'workflowId': wf_id}))}&limit=10")
    items = as_list(body)
    saved = []
    for ex in items:
        eid = ex.get("id")
        s2, full = call("GET", f"/rest/executions/{eid}?includeData=true")
        out = os.path.join(ROOT, "evidence", f"exec-{tag}-{eid}.json")
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(full.get("data", full), fh, indent=2)
        saved.append((eid, ex.get("status"), out))
    return saved


def load_json(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def wait_api_ready(tries=45):
    """healthz answers early; the REST API first replies with the plain
    text 'n8n is starting up. Please wait'. Wait until it serves JSON."""
    for _ in range(tries):
        status, body = call("GET", "/rest/workflows")
        raw = body.get("raw", "") if isinstance(body, dict) else ""
        if status in (200, 401, 403) and "starting up" not in raw:
            return True
        time.sleep(2)
    return False


def main():
    assert wait_ready(), "n8n did not become ready"
    print("n8n is ready")
    assert wait_api_ready(), "REST API did not finish starting"
    print("REST API ready")
    ensure_login()

    ids = {}
    for fn in ["lead-intake.json", "invoice-extraction.json", "rescue-broken.json", "rescue-fixed.json"]:
        wid = import_workflow(fn)
        activate(wid)
        ids[fn] = wid
    time.sleep(2)

    print("\n--- (a) Lead intake, batch 1 ---")
    print(post_webhook("lead-intake", load_json("test-data/leads-batch1.json")))
    print("--- (a) Lead intake, batch 2 ---")
    print(post_webhook("lead-intake", load_json("test-data/leads-batch2.json")))

    print("\n--- (b) Invoice extraction ---")
    print(post_webhook("invoice-batch", {"trigger": "sample-run"}))

    print("\n--- (c) Rescue, broken ---")
    print(post_webhook("orders-broken", load_json("test-data/orders.json")))
    print("--- (c) Rescue, fixed ---")
    print(post_webhook("orders-fixed", load_json("test-data/orders.json")))

    print("\n--- executions ---")
    for fn, tag in [("lead-intake.json", "lead-intake"), ("invoice-extraction.json", "invoice-extraction"),
                    ("rescue-broken.json", "rescue-broken"), ("rescue-fixed.json", "rescue-fixed")]:
        for eid, status, out in fetch_executions(ids[fn], tag):
            print(tag, "execution", eid, "status:", status, "->", out)

    print("\n--- output files ---")
    for rel in ["evidence/leads_table_snapshot.csv", "evidence/invoices_table.csv",
                "evidence/invoice_exceptions.csv", "evidence/notifications.log"]:
        p = os.path.join(ROOT, rel)
        if os.path.exists(p):
            with open(p, encoding="utf-8", errors="replace") as fh:
                content = fh.read()
            print(f"### {rel} ({len(content)} bytes)")
            print(content[:1500])
        else:
            print(f"### {rel} MISSING")


if __name__ == "__main__":
    main()
