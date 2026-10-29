#!/usr/bin/env bash
# email-auth.sh <domain> [...] — DNS-only email authentication audit (SPF / DKIM / DMARC / MX).
# Works without local DNS: queries Cloudflare then Google DoH over HTTPS.
# Usage: ./scripts/email-auth.sh fastdiscountfinder.com
set -u

doh() { # doh <name> <type> -> one answer per line (truncated)
  local name="$1" type="$2" out
  out=$(curl -s --max-time 12 -H 'accept: application/dns-json' \
        "https://cloudflare-dns.com/dns-query?name=${name}&type=${type}" 2>/dev/null)
  echo "$out" | python3 -c '
import json,sys
try: d=json.load(sys.stdin)
except Exception: sys.exit(0)
for a in d.get("Answer",[]):
    if a.get("type") in (5,15,16): print(a["data"].strip("\""))
' 2>/dev/null | tr -d '"'
  if [ -z "$out" ]; then
    curl -s --max-time 12 "https://dns.google/resolve?name=${name}&type=${type}" 2>/dev/null | python3 -c '
import json,sys
try: d=json.load(sys.stdin)
except Exception: sys.exit(0)
for a in d.get("Answer",[]):
    if a.get("type") in (5,15,16): print(a["data"].strip("\""))
' 2>/dev/null | tr -d '"'
  fi
}

SELECTORS="brevo1 brevo2 mail mail2 mta ml mailer send email dkim s1 s2 k1 google selzy mlsend mailersend resend mandrill"

audit() {
  local d="$1" spf_count spf dkim_found="" dmarc mx
  echo "================ $d ================"

  # SPF — must exist exactly once, and must not be >10 lookups (we only flag the basics)
  spf=$(doh "$d" TXT | grep -i '^v=spf1' || true)
  spf_count=$(printf '%s' "$spf" | grep -c 'v=spf1' || true)
  if [ "$spf_count" -eq 0 ]; then
    echo "SPF   : MISSING"; spf_ok=0
  elif [ "$spf_count" -gt 1 ]; then
    echo "SPF   : $spf_count records -> PERMERROR (must be exactly one)"; spf_ok=0
  else
    echo "SPF   : $spf"
    echo "        all=$(echo "$spf" | grep -oE '(~all|-all|\?all|\+all)' | tail -1)  includes=$(echo "$spf" | grep -oE 'include:[^ ]+' | wc -l | tr -d ' ')"
    spf_ok=1
    echo "$spf" | grep -oE 'include:[^ ]+' | sed 's/^/        /'
  fi

  # DKIM — look for the selectors ESPs actually publish
  for s in $SELECTORS; do
    v=$(doh "${s}._domainkey.${d}" CNAME)
    [ -z "$v" ] && v=$(doh "${s}._domainkey.${d}" TXT | head -1)
    if [ -n "$v" ]; then
      echo "DKIM  : ${s}._domainkey -> ${v:0:110}"
      dkim_found="${dkim_found}${s} "
    fi
  done
  [ -z "$dkim_found" ] && echo "DKIM  : none of the common selectors resolve -> NO DKIM"

  # DMARC
  dmarc=$(doh "_dmarc.${d}" TXT | grep -i '^v=DMARC1' || true)
  echo "DMARC : ${dmarc:-MISSING}"

  # MX / receivability
  mx=$(doh "$d" MX | head -3 | tr '\n' ' ')
  echo "MX    : ${mx:-none}"

  # Verdict
  if [ "$spf_ok" = 1 ] && [ -n "$dkim_found" ] && [ -n "$dmarc" ]; then
    echo "VERDICT: AUTHED  (spf + dkim[${dkim_found% }] + dmarc)"
  elif [ "$spf_ok" = 1 ] && [ -n "$dkim_found" ]; then
    echo "VERDICT: PARTIAL (spf + dkim, no DMARC) -> deliverable, weak policy"
  else
    echo "VERDICT: NOT AUTHED (missing $([ "$spf_ok" = 0 ] && echo SPF)[$([ -z "$dkim_found" ] && echo ' DKIM')]) -> do not cold-send from this domain"
  fi
  echo
}

[ $# -eq 0 ] && { echo "usage: $0 <domain> [domain...]"; exit 2; }
for d in "$@"; do audit "$d"; done
