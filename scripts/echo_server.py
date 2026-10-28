#!/usr/bin/env python3
"""Local notification stand-in for the automation proof sample.

Stands in for Slack / email / Teams notifications in a real client build.
Listens on http://127.0.0.1:9999/notify, appends every POST body it receives
to ../evidence/notifications.log (one JSON object per line, timestamped),
and replies 200 {"received": true}. Local only - no external service.
"""
import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "evidence", "notifications.log")


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode("utf-8", "replace")
        entry = {"at": datetime.now(timezone.utc).isoformat(), "path": self.path, "body": body}
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
        payload = b'{"received": true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):  # keep stdout quiet
        pass


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 9999), Handler).serve_forever()
