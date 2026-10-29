#!/usr/bin/env bash
# go-live.sh [--send] — one-shot: check API access -> pick authed sender+list -> preflight -> draft -> (send)
# Refuses to do anything expensive until the account is reachable and the content passes preflight.
set -u
cd "$(dirname "$0")/.." || exit 1
ENVF="$HOME/.secrets/brevo.env"
HTML="email/edu-custom-2026-10-29.html"
TXT="email/edu-custom-2026-10-29.txt"
SUBJ="Your custom .edu email + 200+ student discounts"
NAME="EDU custom $(date +%F)"
SEND=0
for a in "$@"; do case "$a" in --send) SEND=1;; --name=*) NAME="${a#*=}";; --subject=*) SUBJ="${a#*=}";; --html=*) HTML="${a#*=}";; esac; done

[ -f "$ENVF" ] || { echo "missing $ENVF"; exit 2; }
set -a; . "$ENVF"; set +a
KEY="${BREVO_API_KEY:-}"
[ -n "$KEY" ] || { echo "BREVO_API_KEY empty in $ENVF"; exit 2; }

api() { # api <method> <path> [body]
  local m="$1" p="$2" b="${3:-}"
  if [ -n "$b" ]; then
    curl -s --max-time 40 -X "$m" -H "api-key: $KEY" -H "accept: application/json" -H "content-type: application/json" -d "$b" "https://api.brevo.com/v3$p"
  else
    curl -s --max-time 40 -X "$m" -H "api-key: $KEY" -H "accept: application/json" "https://api.brevo.com/v3$p"
  fi
}

echo "== 1. API access =="
acct=$(api GET /account)
if echo "$acct" | grep -q "unrecognised IP"; then
  ip=$(curl -s --max-time 15 https://api.ipify.org)
  echo "  BLOCKED: this IP ($ip) is not allowlisted on the Brevo account."
  echo "  Approve it here, then re-run:  https://app.brevo.com/security/authorised_ips"
  echo "  (a carrier CGNAT IP rotates — prefer adding 102.213.179.0/24 or turning IP restriction off)"
  exit 4
fi
if ! echo "$acct" | grep -q '"email"'; then echo "  unexpected /account response: $(echo "$acct" | head -c 200)"; exit 4; fi
echo "  ok: $(echo "$acct" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("email"), "| plan:", (d.get("plan") or [{}])[0].get("type","?") if isinstance(d.get("plan"),list) else d.get("plan"))' 2>/dev/null)"

echo "== 2. Sending identity =="
doms=$(api GET /senders/domains)
authed=$(echo "$doms" | python3 -c '
import json,sys
try: d=json.load(sys.stdin)
except Exception: sys.exit(0)
for x in d.get("domains",[]):
    if x.get("authenticated") and x.get("verified"): print(x["domain_name"])
' 2>/dev/null)
senders=$(api GET /senders)
echo "  verified senders:"; echo "$senders" | python3 -c '
import json,sys
try: d=json.load(sys.stdin)
except Exception: sys.exit(0)
for s in d.get("senders",[]): print("   -", s.get("email"), "(active)" if s.get("active") else "(inactive)")
' 2>/dev/null
echo "  authenticated domains: ${authed:-NONE}"
if [ -z "$authed" ]; then
  echo "  WARNING: no authenticated domain -> SPF/DKIM will not align. Mail will mostly land in spam."
  echo "           Authenticate a domain in Brevo (Senders, Domains & IPs -> Domains) before a real blast."
  SENDER_DOMAIN="${BREVO_SENDER_EMAIL#*@}"
else
  SENDER_DOMAIN=$(echo "$authed" | head -1)
fi

echo "== 3. Audience =="
lists=$(api GET "/contacts/lists?limit=50")
echo "$lists" | python3 -c '
import json,sys
try: d=json.load(sys.stdin)
except Exception: sys.exit(0)
for l in d.get("lists",[]): print("   -", l.get("id"), l.get("name"), "| subscribers:", l.get("totalSubscribers"))
' 2>/dev/null
sel_list="${BREVO_LIST_ID:-}"
echo "  using list id: ${sel_list:-MISSING (set BREVO_LIST_ID or pass env)}"

echo "== 4. Preflight ($SENDER_DOMAIN) =="
if ! ./scripts/inbox-preflight.sh "$SENDER_DOMAIN" "$HTML" "$SUBJ" > $HOME/tmp/pf.$$ 2>&1; then rc=$?; else rc=0; fi
sed -e 's/\x1b\[[0-9;]*m//g' $HOME/tmp/pf.$$ | sed -n '/== 2\./,$p'; rm -f $HOME/tmp/pf.$$
if [ "${rc:-1}" -ne 0 ] && [ "$SEND" -eq 1 ]; then echo "  PREFLIGHT FAILED ($rc blocker(s)) — refusing to send."; exit 5; elif [ "${rc:-1}" -ne 0 ]; then echo "  PREFLIGHT: $rc blocker(s) — draft only (will not send)."; fi

echo "== 5. Draft =="
args=(--html "$HTML" --subject "$SUBJ" --name "$NAME")
[ -n "$sel_list" ] && args+=(--list-id "$sel_list")
[ "$SEND" -eq 1 ] && args+=(--send)
./scripts/brevo-draft.py "${args[@]}"
