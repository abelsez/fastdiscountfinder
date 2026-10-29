#!/usr/bin/env python3
"""multi-send.py — spread one campaign across every sender you have keys for.

Why: Brevo free caps at 300 sends/day per *account*, so "the whole list" (1,330 unique
contacts) is 5 days on one provider and 3 on two. This script treats each provider as a
bucket with its own daily cap, fills buckets round-robin, keeps a local ledger so nothing is
sent twice, and skips a provider the moment it errors.

Providers (keys in ~/.secrets/senders.env, all optional):
  BREVO_API_KEY=        BREVO_DAILY=300      BREVO_FROM=abel@smartworld.press
  MAILJET_API_KEY=      MAILJET_SECRET=      MAILJET_DAILY=200   MAILJET_FROM=
  RESEND_API_KEY=       RESEND_DAILY=100     RESEND_FROM=
  MAILERSEND_API_KEY=   MAILERSEND_DAILY=100 MAILERSEND_FROM=
  SMTP_HOST/PORT/USER/PASS                   SMTP_DAILY=100     SMTP_FROM=

usage:
  multi-send.py --status                 # per-provider capacity + ledger state
  multi-send.py --plan                   # who gets which provider today, no sending
  multi-send.py --send --subject "..." --html file.html [--batch 500]
"""
from __future__ import annotations

import argparse
import base64
import json
import smtplib
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "state" / "multi-send-ledger.json"
ENVF = Path.home() / ".secrets" / "senders.env"
LISTS = [30, 22, 17, 32, 31, 28, 5, 14, 27, 26, 29, 9, 20, 10, 18, 11, 7, 6, 8]


def env() -> dict[str, str]:
    out = {}
    for f in (ENVF, Path.home() / ".secrets" / "brevo.env"):
        if not f.exists():
            continue
        for line in f.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                out.setdefault(k.strip(), v.strip().strip('"'))
    return out


def ledger() -> dict:
    if LEDGER.exists():
        return json.loads(LEDGER.read_text())
    return {"sent": {}, "by_day": {}}


def save(l: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(l, indent=1))
    LEDGER.chmod(0o600)


def post(url: str, payload: dict, headers: dict, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                 headers={"accept": "application/json", "content-type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode()[:200]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]
    except Exception as e:  # noqa: BLE001
        return 0, str(e)[:120]


def brevo_capacity(e: dict) -> int:
    key = e.get("BREVO_API_KEY")
    if not key:
        return 0
    req = urllib.request.Request("https://api.brevo.com/v3/account", headers={"api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            d = json.loads(r.read().decode())
        return int((d.get("plan") or [{}])[0].get("credits") or 0)
    except Exception:  # noqa: BLE001
        return 0


def providers(e: dict, l: dict) -> list[dict]:
    today = date.today().isoformat()
    used_today = l["by_day"].get(today, {})
    out = []

    def cap(name, key, daily):
        return max(0, int(daily) - int(used_today.get(name, 0)))

    if e.get("BREVO_API_KEY"):
        out.append({"name": "brevo", "left": min(cap("brevo", None, e.get("BREVO_DAILY", 300)), brevo_capacity(e)),
                    "from": e.get("BREVO_FROM", "abel@smartworld.press")})
    if e.get("MAILJET_API_KEY") and e.get("MAILJET_SECRET"):
        out.append({"name": "mailjet", "left": cap("mailjet", None, e.get("MAILJET_DAILY", 200)),
                    "from": e.get("MAILJET_FROM", "")})
    if e.get("RESEND_API_KEY"):
        out.append({"name": "resend", "left": cap("resend", None, e.get("RESEND_DAILY", 100)),
                    "from": e.get("RESEND_FROM", "")})
    if e.get("MAILERSEND_API_KEY"):
        out.append({"name": "mailersend", "left": cap("mailersend", None, e.get("MAILERSEND_DAILY", 100)),
                    "from": e.get("MAILERSEND_FROM", "")})
    if e.get("SMTP_HOST") and e.get("SMTP_USER"):
        out.append({"name": "smtp", "left": cap("smtp", None, e.get("SMTP_DAILY", 100)),
                    "from": e.get("SMTP_FROM", "")})
    return out


def recipients(e: dict, l: dict, limit: int) -> list[str]:
    key = e.get("BREVO_API_KEY")
    if not key:
        return []
    out: list[str] = []
    for lid in LISTS:
        off = 0
        while len(out) < limit:
            req = urllib.request.Request(f"https://api.brevo.com/v3/contacts?listIds={lid}&limit=500&offset={off}",
                                         headers={"api-key": key, "accept": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=50) as r:
                    cs = (json.loads(r.read().decode()).get("contacts") or [])
            except Exception:  # noqa: BLE001
                cs = []
            if not cs:
                break
            for c in cs:
                em = (c.get("email") or "").lower()
                if em and em not in l["sent"] and not c.get("emailBlacklisted") and em not in out:
                    out.append(em)
            if len(cs) < 500:
                break
            off += 500
        if len(out) >= limit:
            break
    return out


def send_one(p: dict, e: dict, to: str, subject: str, html: str, text: str) -> tuple[bool, str]:
    if p["name"] == "brevo":
        st, body = post("https://api.brevo.com/v3/smtp/email",
                        {"sender": {"name": "Fast Discount Finder", "email": p["from"]},
                         "to": [{"email": to}], "replyTo": {"email": "jmaclive101@gmail.com"},
                         "subject": subject, "htmlContent": html, "textContent": text},
                        {"api-key": e["BREVO_API_KEY"]})
        return st in (200, 201), f"{st} {body[:60]}"
    if p["name"] == "mailjet":
        auth = base64.b64encode(f"{e['MAILJET_API_KEY']}:{e['MAILJET_SECRET']}".encode()).decode()
        st, body = post("https://api.mailjet.com/v3.1/send",
                        {"Messages": [{"From": {"Email": p["from"]}, "To": [{"Email": to}],
                                       "Subject": subject, "HTMLPart": html, "TextPart": text}]},
                        {"Authorization": f"Basic {auth}"})
        return st in (200, 201), f"{st} {body[:60]}"
    if p["name"] == "resend":
        st, body = post("https://api.resend.com/emails",
                        {"from": p["from"], "to": [to], "subject": subject, "html": html, "text": text},
                        {"Authorization": f"Bearer {e['RESEND_API_KEY']}"})
        return st in (200, 201), f"{st} {body[:60]}"
    if p["name"] == "mailersend":
        st, body = post("https://api.mailersend.com/v1/email",
                        {"from": {"email": p["from"]}, "to": [{"email": to}], "subject": subject,
                         "html": html, "text": text},
                        {"Authorization": f"Bearer {e['MAILERSEND_API_KEY']}"})
        return st in (202, 200), f"{st} {body[:60]}"
    if p["name"] == "smtp":
        m = EmailMessage()
        m["Subject"], m["From"], m["To"] = subject, p["from"], to
        m["Reply-To"] = "jmaclive101@gmail.com"
        m.set_content(text)
        m.add_alternative(html, subtype="html")
        try:
            with smtplib.SMTP(e["SMTP_HOST"], int(e.get("SMTP_PORT", 587)), timeout=45) as s:
                s.ehlo(); s.starttls(context=ssl.create_default_context()); s.ehlo()
                s.login(e["SMTP_USER"], e["SMTP_PASS"])
                s.send_message(m)
            return True, "smtp ok"
        except Exception as err:  # noqa: BLE001
            return False, f"smtp {err}"
    return False, "unknown provider"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--send", action="store_true")
    ap.add_argument("--subject", default="Your custom .edu email + 200+ student discounts")
    ap.add_argument("--html", default="email/edu-custom-2026-10-29.html")
    ap.add_argument("--text", default="email/edu-custom-2026-10-29.txt")
    ap.add_argument("--batch", type=int, default=0, help="cap total sends this run")
    args = ap.parse_args()

    e, l = env(), ledger()
    ps = providers(e, l)
    total_cap = sum(p["left"] for p in ps)

    if args.status or args.plan:
        print(f"ledger: {len(l['sent'])} unique addresses already sent")
        print(f"{'provider':12} {'left today':>10}  from")
        for p in ps:
            print(f"{p['name']:12} {p['left']:>10}  {p['from']}")
        print(f"{'TOTAL':12} {total_cap:>10}")
        if args.plan:
            want = args.batch or total_cap
            todo = recipients(e, l, want)
            print(f"\nwould send {min(len(todo), total_cap)} now; queue head: {todo[:5]}")
        return 0

    if not args.send:
        print("nothing to do: pass --send (or --plan/--status)")
        return 0

    html = (ROOT / args.html).read_text()
    text = (ROOT / args.text).read_text()
    todo = recipients(e, l, args.batch or total_cap)
    print(f"queue: {len(todo)} | capacity: {total_cap}")
    sent = failed = 0
    idx = 0
    for p in ps:
        for _ in range(p["left"]):
            if idx >= len(todo):
                break
            to = todo[idx]; idx += 1
            ok, msg = send_one(p, e, to, args.subject, html, text)
            if ok:
                l["sent"][to] = {"at": time.strftime("%FT%TZ", time.gmtime()), "via": p["name"]}
                l["by_day"].setdefault(date.today().isoformat(), {}).setdefault(p["name"], 0)
                l["by_day"][date.today().isoformat()][p["name"]] += 1
                sent += 1
            else:
                failed += 1
                print(f"  FAIL {p['name']} {to[:24]}… {msg}")
                if "401" in msg or "403" in msg or "smtp" in msg:
                    print(f"  provider {p['name']} looks unusable, skipping for this run")
                    break
            if sent % 25 == 0:
                save(l)
        if idx >= len(todo):
            break
    save(l)
    print(f"done: {sent} sent, {failed} failed, {len(l['sent'])} total in ledger")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
