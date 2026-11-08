#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "\${BASH_SOURCE[0]}")" && pwd)"
YLANG_COMPILER="\${YLANG_COMPILER:-ylang}"
OUTPUT="$ROOT/server/linux-inspector-ylang"

if ! command -v "$YLANG_COMPILER" >/dev/null 2>&1; then
    printf 'error: YLang compiler not found: %s\n' "$YLANG_COMPILER" >&2
    exit 127
fi

mkdir -p "$ROOT/server"

printf '%s\n' '[1/2] Checking YLang source...'
"$YLANG_COMPILER" check "$ROOT/server.yl"

printf '%s\n' '[2/2] Building Linux Inspector...'
"$YLANG_COMPILER" build "$ROOT/server.yl" -o "$OUTPUT"
chmod 755 "$OUTPUT"

printf 'Built: %s\n' "$OUTPUT"
