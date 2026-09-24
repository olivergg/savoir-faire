#!/usr/bin/env bash
# Periodic secret-leak check over Claude Code session transcripts.
#
# Runs `scan_secrets.py scan` (deterministic; never prints a secret value),
# diffs the result against the last run, and — only when it changed — writes a
# dated report and posts a desktop notification. Remediation stays
# interactive: run `/session-secret-audit` in Claude Code to review and clean.
#
# Schedule it with com.savoir-faire.secret-audit.plist (launchd) or cron.
set -euo pipefail

SCAN="${SECRET_SCAN:-$(dirname "$0")/scan_secrets.py}"
OUT="${SECRET_AUDIT_DIR:-$HOME/.claude/secret-audit}"
LAST="$OUT/last.txt"

mkdir -p "$OUT"

if [[ ! -f "$SCAN" ]]; then
  echo "scanner not found: $SCAN (expected next to this script)" >&2
  exit 127
fi

now="$(python3 "$SCAN" scan 2>/dev/null || true)"

# digest = severity + pattern + count + path, sorted; drops the mtime column so a
# harmless file-touch doesn't count as a change.
digest() {
  printf '%s\n' "$1" | awk 'NR>2 && NF {print $1, $3, $4, $NF}' | sort
}

new_digest="$(digest "$now")"
old_digest=""
[[ -f "$LAST" ]] && old_digest="$(digest "$(cat "$LAST")")"

crit=$(printf '%s\n' "$new_digest"  | grep -c '^critical' || true)
high=$(printf '%s\n' "$new_digest"  | grep -c '^high' || true)
total=$(printf '%s\n' "$new_digest" | grep -c . || true)

# one line like: "critical slack_token ×4 · high google_api_key ×6"
breakdown="$(printf '%s\n' "$new_digest" | awk '
  $1=="critical" || $1=="high" { c[$1" "$2] += $3 }
  END { for (k in c) printf "%s ×%d\n", k, c[k] }' | sort | paste -sd ' · ' -)"

printf '%s\n' "$now" > "$LAST"

if [[ "$new_digest" == "$old_digest" ]]; then
  echo "no change — $total findings ($crit critical, $high high)"
  exit 0
fi

stamp="$(date +%Y-%m-%dT%H-%M)"
report="$OUT/report-$stamp.txt"
{
  echo "Session secret audit — $stamp"
  echo "$total findings: $crit critical, $high high"
  echo
  echo "$now"
  echo
  echo "Review & clean: run /session-secret-audit in Claude Code."
  echo "Redaction is not rotation — rotate any confirmed-real credential."
} > "$report"
ln -sf "$report" "$OUT/latest.txt"

echo "changed — wrote $report"

# Notify. terminal-notifier is reliable and clickable; osascript notifications
# are attributed to Script Editor and show empty unless that app is allowed to
# send notifications (System Settings > Notifications > Script Editor).
title="Session secret audit"
subtitle="$total findings — $crit critical, $high high (changed)"
message="${breakdown:-see report}
Click to open the report"

if command -v terminal-notifier >/dev/null 2>&1; then
  terminal-notifier -title "$title" -subtitle "$subtitle" -message "$message" \
    -sound Basso -group secret-audit -open "file://$report" || true
elif command -v osascript >/dev/null 2>&1; then
  osascript -e "display notification \"${breakdown:-see report}\" with title \"$title\" subtitle \"$subtitle\" sound name \"Basso\"" \
    || echo "notification failed (allow Script Editor in Notifications settings, or: brew install terminal-notifier)"
fi

# non-zero so a scheduler / CI surfaces it
exit 1
