#!/usr/bin/env python3
"""Create a Brevo *draft* email campaign from an HTML file. Never sends.

usage:
  brevo-draft.py --html email/edu-custom-2026-10-29.html \
                 --subject "Your custom .edu email + 200+ student discounts" \
                 --name "EDU custom 2026-10-29" [--list-id 3] [--dry-run]

Credentials come from ~/.secrets/brevo.env (BREVO_API_KEY, BREVO_SENDER_EMAIL,
BREVO_SENDER_NAME, BREVO_LIST_ID). The key is never printed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ENV = Path.home() / ".secrets" / "brevo.env"
API = "https://api.brevo.com/v3/emailCampaigns"


def load_env(path: Path = ENV) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        values[k.strip()] = v.strip()
    return values


def mask(secret: str) -> str:
    return f"set(len={len(secret)})" if secret else "MISSING"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--list-id", action="append", default=[])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    env = load_env()
    key = env.get("BREVO_API_KEY", "")
    sender_email = env.get("BREVO_SENDER_EMAIL", "")
    sender_name = env.get("BREVO_SENDER_NAME", "Fast Discount Finder")
    list_ids = [int(x) for x in (args.list_id or [env.get("BREVO_LIST_ID", "")]) if x]

    html = Path(args.html).read_text(encoding="utf-8")
    payload = {
        "name": args.name,
        "subject": args.subject,
        "sender": {"name": sender_name, "email": sender_email},
        "type": "classic",
        "htmlContent": html,
        "recipients": {"listIds": list_ids},
    }

    print(f"html      : {args.html} ({len(html)} bytes)")
    print(f"subject   : {args.subject}")
    print(f"name      : {args.name}")
    print(f"sender    : {sender_name} <{sender_email or 'MISSING'}>")
    print(f"listIds   : {list_ids or 'MISSING'}")
    print(f"api key   : {mask(key)}")
    print("mode      : draft (no send-at, no scheduling)")

    if args.dry_run:
        print("dry-run   : payload built, not posted")
        return 0
    if not key or not sender_email:
        print("ERROR: fill BREVO_API_KEY and BREVO_SENDER_EMAIL in ~/.secrets/brevo.env", file=sys.stderr)
        return 2
    if not list_ids:
        print("ERROR: no list id (--list-id or BREVO_LIST_ID)", file=sys.stderr)
        return 2

    req = urllib.request.Request(
        API,
        data=json.dumps(payload).encode(),
        headers={"api-key": key, "accept": "application/json", "content-type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            body = resp.read().decode()
            print(f"HTTP {resp.status} -> {body[:300]}")
            return 0 if resp.status in (200, 201) else 1
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()[:500]
        print(f"HTTP {exc.code} -> {detail}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"network error: {exc.reason}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
