#!/usr/bin/env bash
# The ASCII gate: fails when a tracked file holds a non-ASCII character, except the files
# listed in .ascii-allow (one path per line, `#` starts a comment).
# Usage: scripts/ascii-check.sh   (run from anywhere inside the repository)
set -euo pipefail

root="$(git rev-parse --show-toplevel)"
cd "$root"

allowed=()
if [ -f .ascii-allow ]; then
  while IFS= read -r line; do
    line="${line%%#*}"
    line="${line%"${line##*[![:space:]]}"}"
    [ -n "$line" ] && allowed+=("$line")
  done < .ascii-allow
fi

status=0
while IFS= read -r -d '' file; do
  [ -f "$file" ] || continue
  for ok in "${allowed[@]+"${allowed[@]}"}"; do
    [ "$file" = "$ok" ] && continue 2
  done
  if LC_ALL=C grep -nP '[^\x00-\x7F]' -- "$file" | head -5 | sed "s|^|$file:|" | grep .; then
    status=1
  fi
done < <(git ls-files -z)

[ "$status" -eq 0 ] && echo "ascii-check: ok"
exit "$status"
