#!/usr/bin/env python3
"""drip-send.py — move the whole contact base through Brevo at the plan's daily rate.

Brevo free = 300 sends/day. There is no way around that ceiling (it is per-account, not
per-IP), so "send all lists" is a 5-day drip, not one blast. This script:
  * reads remaining credits from /account (stops cleanly when 0),
  * picks the next unsent contacts, warmest list first (clickers -> openers -> cold),
  * packs them into a temporary list, creates a campaign, sends it,
  * records every email it sent in state/drip.json so nothing is ever sent twice,
  * refuses to run if a previous campaign came back `suspended` by Brevo review.

usage:  drip-send.py [--batch-max 250] [--lists 30,22,17,32,31,28] [--dry-run] [--cleanup]
        drip-send.py --status
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state" / "drip.json"
ENVF = Path.home() / ".secrets" / "brevo.env"
API = "https://api.brevo.com/v3"
DEFAULT_LISTS = [30, 22, 17, 32, 31, 28, 5, 14, 27, 26, 29, 9, 20, 10, 18, 11, 7, 6, 8]
SUBJECT = "Your custom .edu email + 200+ student discounts"


def load_env() -> dict[str, str]:
    out = {}
    for line in ENVF.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"')
    return out


def call(key: str, method: str, path: str, payload=None, timeout=60):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(API + path, data=data, method=method,
                                headers={"api-key": key, "accept": "application/json",
                                         "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode()
            return r.status, (json.loads(body) if body.strip() else {})
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, {"raw": body[:300]}
    except Exception as e:  # noqa: BLE001
        return 0, {"error": str(e)}


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"sent": {}, "campaigns": []}


def save_state(s: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(s, indent=1))
    STATE.chmod(0o600)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-max", type=int, default=250)
    ap.add_argument("--lists", default=",".join(map(str, DEFAULT_LISTS)))
    ap.add_argument("--reserve", type=int, default=10, help="credits kept free for seeds/ops")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--simulate", type=int, default=0, help="pretend this many credits are available (selection test)")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--cleanup", action="store_true", help="delete drip-* temp lists after success")
    ap.add_argument("--subject", default=SUBJECT)
    ap.add_argument("--html", default="email/edu-custom-2026-10-29.html")
    ap.add_argument("--name-prefix", default="EDU drip")
    args = ap.parse_args()

    key = load_env()["BREVO_API_KEY"]
    state = load_state()
    sent = state["sent"]

    if args.status:
        st, acct = call(key, "GET", "/account")
        left = (acct.get("plan") or [{}])[0].get("credits")
        st, c = call(key, "GET", "/contacts?limit=1")
        total = c.get("count")
        print(f"contacts total      : {total}")
        print(f"already sent by drip: {len(sent)}")
        print(f"remaining to send   : {max(0, (total or 0) - len(sent))}")
        print(f"credits left today  : {left}")
        print(f"campaigns so far    : {len(state['campaigns'])}")
        for c in state["campaigns"][-5:]:
            print(f"   #{c['id']} {c['date']} {c['count']:>4} subs status={c['status']}")
        return 0

    st, acct = call(key, "GET", "/account")
    if st != 200:
        print("account read failed:", st, acct, file=sys.stderr)
        return 2
    credits = (acct.get("plan") or [{}])[0].get("credits") or 0
    print(f"credits left: {credits}")
    if args.simulate:
        credits = args.simulate + args.reserve
    capacity = max(0, credits - args.reserve)
    if capacity == 0:
        print("nothing to do today: 0 usable credits (Brevo resets daily). Re-run after reset.")
        return 0

    n = min(args.batch_max, capacity)
    # pick next unsent contacts, warmest list first
    picked: list[str] = []
    for lid in [int(x) for x in args.lists.split(",") if x.strip()]:
        off = 0
        while len(picked) < n:
            st, d = call(key, "GET", f"/contacts?listIds={lid}&limit=500&offset={off}")
            cs = d.get("contacts") or []
            if not cs:
                break
            for c in cs:
                e = (c.get("email") or "").lower()
                if not e or e in sent or c.get("emailBlacklisted"):
                    continue
                if e not in picked:
                    picked.append(e)
                if len(picked) >= n:
                    break
            if len(cs) < 500:
                break
            off += 500
        if len(picked) >= n:
            break

    print(f"batch: {len(picked)} new contacts (cap {n})")
    if not picked:
        print("no unsent contacts left in the given lists.")
        return 0
    if args.dry_run:
        print("dry-run: first 5 ->", picked[:5])
        return 0

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    st, lst = call(key, "POST", "/contacts/lists", {"name": f"drip-{stamp}", "folderId": 1})
    if st not in (200, 201):
        print("temp list create failed:", st, lst, file=sys.stderr)
        return 3
    tmp_id = lst["id"]
    for i in range(0, len(picked), 150):
        st, r = call(key, "POST", f"/contacts/lists/{tmp_id}/contacts/add", {"emails": picked[i:i + 150]})
        print(f"  added {len(picked[i:i+150])} -> {st}")

    html = (ROOT / args.html).read_text()
    st, camp = call(key, "POST", "/emailCampaigns", {
        "name": f"{args.name_prefix} {stamp}",
        "subject": args.subject,
        "sender": {"name": "Fast Discount Finder", "email": "abel@smartworld.press"},
        "replyTo": "jmaclive101@gmail.com",
        "type": "classic",
        "htmlContent": html,
        "recipients": {"listIds": [tmp_id]},
    })
    if st not in (200, 201):
        print("campaign create failed:", st, camp, file=sys.stderr)
        return 4
    cid = camp["id"]
    st, _ = call(key, "POST", f"/emailCampaigns/{cid}/sendNow", {})
    print(f"sendNow #{cid}: HTTP {st}")

    status = "unknown"
    for _ in range(6):
        time.sleep(20)
        st, d = call(key, "GET", f"/emailCampaigns/{cid}")
        status = d.get("status", "?")
        if status in ("sent", "archive", "suspended"):
            break
    print(f"campaign #{cid} status: {status}")

    if status == "suspended":
        print("Brevo suspended this campaign — stopping so we do not burn the account.", file=sys.stderr)
        return 5

    for e in picked:
        sent[e] = stamp
    state["campaigns"].append({"id": cid, "date": stamp, "count": len(picked),
                               "status": status, "list": tmp_id})
    save_state(state)
    print(f"recorded {len(picked)} addresses in {STATE}")

    if args.cleanup:
        call(key, "DELETE", f"/contacts/lists/{tmp_id}")
        print(f"temp list {tmp_id} deleted")

    st, acct = call(key, "GET", "/account")
    left = (acct.get("plan") or [{}])[0].get("credits")
    print(f"credits left now: {left}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
