#!/usr/bin/env bash
# inbox-preflight.sh <domain> <html-file> [subject]
# Answers one question: will this campaign land in the inbox from <domain>?
# Checks DNS auth (SPF/DKIM/DMARC) + content signals email filters score on.
# Exit code = number of FAILs (0 = safe to send).
set -u
DIR=$(cd "$(dirname "$0")" && pwd)

fail=0; warn=0
ok()   { printf '  \033[32mOK\033[0m    %s\n' "$1"; }
bad()  { printf '  \033[31mFAIL\033[0m  %s\n     fix: %s\n' "$1" "$2"; fail=$((fail+1)); }
wrn()  { printf '  \033[33mWARN\033[0m  %s\n     fix: %s\n' "$1" "$2"; warn=$((warn+1)); }

D=${1:-}; H=${2:-}; SUBJ=${3:-}
[ -z "$D" ] || [ -z "$H" ] && { echo "usage: $0 <sending-domain> <html-file> [subject]"; exit 2; }
[ -f "$H" ] || { echo "no such file: $H"; exit 2; }

echo "== 1. DNS authentication for $D =="
auth=$("$DIR/email-auth.sh" "$D" 2>/dev/null)
echo "$auth" | sed 's/^/  /'
spf=$(echo "$auth" | grep -c '^SPF   : v=spf1')
dkim=$(echo "$auth" | grep -cE '^DKIM  : [a-z0-9]+\._domainkey -> ')
dmarc_p=$(echo "$auth" | grep -oE 'p=(none|quarantine|reject)' | head -1)

[ "$spf" -eq 1 ] && ok "SPF present, single record" || bad "SPF missing or duplicated" "add ONE TXT v=spf1 ... include:<esp> ~all"
[ "$dkim" -ge 1 ] && ok "DKIM selector(s) resolve ($dkim)" || bad "no DKIM" "add the ESP's DKIM CNAMEs (Brevo: brevo1/brevo2._domainkey)"
case "$dmarc_p" in
  p=reject|p=quarantine) ok "DMARC enforcing ($dmarc_p)" ;;
  p=none) wrn "DMARC monitoring only (p=none)" "tighten to p=quarantine after warmup" ;;
  *) bad "no DMARC record" "add TXT _dmarc: v=DMARC1; p=none; rua=mailto:dmarc@$D" ;;
esac

echo
echo "== 2. Content signals ($H) =="
python3 - "$D" "$H" "$SUBJ" <<'PY'
import re, sys, os
domain, path, subj = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(path, encoding='utf-8').read()

text = re.sub(r'<[^>]+>', ' ', s)
text = re.sub(r'&[a-z]+;|&#\d+;', ' ', text)
text = re.sub(r'\s+', ' ', text).strip()
size = len(s.encode())
imgs = len(re.findall(r'<img\b', s, re.I))
links = re.findall(r'href="(https?://[^"]+)"', s)
doms = sorted({re.sub(r'^https?://([^/]+).*', r'\1', l) for l in links})
body_words = len(text.split())

F = []; W = []; O = []
def ok(m): O.append(("OK", m))
def fail(m, f): F.append((m, f))
def warn(m, f): W.append((m, f))

# size / structure
if size < 102_000: ok(f"size {size} B (<102 KB Gmail clip)")
else: fail(f"size {size} B", "Gmail clips >102 KB; split or trim")
if imgs == 0: ok("zero images (text-only renders everywhere)")
elif imgs <= 3: warn(f"{imgs} images", "keep image:text ratio low, add alt text")
else: fail(f"{imgs} images", "reduce images; filters score image-heavy mail")

# text part
txt_part = os.path.splitext(path)[0] + '.txt'
if os.path.exists(txt_part):
    t = open(txt_part, encoding='utf-8').read()
    ok(f"plain-text alternative present ({len(t.split())} words)")
    if '{{ unsubscribe }}' in t: ok("plain text carries unsubscribe placeholder")
else:
    fail("no plain-text part", f"add {os.path.basename(txt_part)} (multipart/alternative improves inbox placement)")

# link hygiene
if len(links) <= 6: ok(f"{len(links)} links")
else: warn(f"{len(links)} links", "more than ~6 links raises bulk-mail score")
if len(doms) <= 2: ok(f"link domains: {', '.join(doms)}")
else: warn(f"{len(doms)} link domains: {', '.join(doms)}", "consolidate to your own domain")
if all(d == domain or d == 'wa.me' for d in doms): ok("all links are your domain or a messaging deep link")
else: warn("links include third-party domains", "link only to your own domain")

# unsubscribe + postal address (CAN-SPAM)
if re.search(r'unsubscribe', s, re.I) or '{{ unsubscribe }}' in s: ok("unsubscribe language present")
else: warn("no unsubscribe wording in body", "Brevo injects its own, but in-body text helps complaints")
if re.search(r'\[\[POSTAL-ADDRESS\]\]', text):
    fail("postal address is still the [[POSTAL-ADDRESS]] placeholder", "replace with the real business address (CAN-SPAM)")
elif re.search(r'\d{1,5}\s+\w+\s+(st|street|ave|avenue|rd|road|blvd|suite|unit)\b', text, re.I):
    ok("physical postal address present (CAN-SPAM)")
else:
    fail("no physical postal address", "CAN-SPAM requires a valid postal address in the footer (add the real one)")

# spam-trigger lexicon
triggers = {
 r'\bguarantee[ds]?\b': 'Guarantee',
 r'\bact now\b': 'Act now',
 r'\brisk[- ]free\b': 'Risk-free',
 r'\b100%\s*(free|guaranteed)': '100% free',
 r'\bno risk\b': 'No risk',
 r'\bclick here\b': 'Click here',
 r'\blimited time\b': 'Limited time',
 r'\bwinner\b': 'Winner',
 r'\bcash\b': 'Cash',
 r'\bmiracle\b': 'Miracle',
}
hits = [lab for pat, lab in triggers.items() if re.search(pat, text, re.I)]
if not hits: ok("no classic spam-trigger phrases")
else: warn("spam-trigger phrases: " + ', '.join(hits), "rephrase (e.g. 'Guarantee' -> 'Backed by' / drop it)")

# yelling / punctuation
words = re.findall(r'\b[A-Z]{4,}\b', text)
caps_ratio = len(words) / max(body_words, 1)
if caps_ratio < 0.03: ok(f"caps ratio {caps_ratio:.1%}")
else: warn(f"caps ratio {caps_ratio:.1%}", "avoid ALL-CAPS words over 3 letters")
exclam = text.count('!')
if exclam <= 2: ok(f"{exclam} exclamation marks")
else: warn(f"{exclam} exclamation marks", "trim to <=2")

# subject
if subj:
    if len(subj) <= 60: ok(f"subject {len(subj)} chars")
    else: warn(f"subject {len(subj)} chars", "keep <=60 so mobile clients don't truncate")
    if subj.isupper(): fail("subject is ALL CAPS", "mixed case")
    if len(re.findall(r'[$!]', subj)) > 2: warn("subject heavy on $ !", "one money figure max")
else:
    warn("no subject passed", "pass it as arg 3 to check length/format")

# preheader
if re.search(r'display\s*:\s*none[^>]*>', s) or 'mso-hide' in s: ok("preheader block present")
else: warn("no hidden preheader", "add a display:none preheader so the preview is controlled")

for kind, msg in O: print(f"  OK    {msg}")
for msg, fix in W: print(f"  WARN  {msg}\n     fix: {fix}")
for msg, fix in F: print(f"  FAIL  {msg}\n     fix: {fix}")
print(f"\n  score: {len(O)} ok / {len(W)} warn / {len(F)} fail")
sys.exit(len(F))
PY
py_rc=$?

echo
echo "== summary =="
echo "  dns auth fails : $fail"
echo "  content fails  : $py_rc"
total=$((fail + py_rc))
if [ "$total" -eq 0 ]; then
  echo "  VERDICT: INBOX-READY (then warm the domain: 20-50/day for 3 days before blasting)"
  exit 0
fi
echo "  VERDICT: $total blocking issue(s) — sending now = spam folder or ESP rejection"
exit "$total"
