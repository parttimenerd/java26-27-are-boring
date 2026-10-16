#!/usr/bin/env bash
set -euo pipefail

# Find image files under img/ that are not referenced in source files.
# Usage: cleanup-unused-images.sh [--delete]
# Default: dry-run (lists unused files). With --delete moves files to .unused-images-<ts>/

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
IMG_DIR="$ROOT_DIR/img"
SEARCH_DIR="$ROOT_DIR"
SOURCE_GLOBS=(
  "--include=*.md"
  "--include=*.vue"
  "--include=*.ts"
  "--include=*.js"
  "--include=*.mjs"
  "--include=*.html"
  "--include=*.json"
)

DELETE=false
if [[ ${1-} == "--delete" ]]; then
  DELETE=true
fi

if [[ ! -d "$IMG_DIR" ]]; then
  echo "No image directory found at: $IMG_DIR"
  exit 0
fi

echo "Scanning images in $IMG_DIR (searching references under $SEARCH_DIR)"

shopt -s nullglob
mapfile -t images < <(find "$IMG_DIR" -type f \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.svg' -o -iname '*.gif' -o -iname '*.webp' \) )
shopt -u nullglob

if [[ ${#images[@]} -eq 0 ]]; then
  echo "No images found."
  exit 0
fi

unused=()

for img in "${images[@]}"; do
  base=$(basename "$img")
  if ! grep -R --line-number --binary-files=without-match -F \
    --exclude-dir=node_modules \
    --exclude-dir=dist \
    --exclude-dir=.git \
    --exclude-dir='.unused-images-*' \
    "${SOURCE_GLOBS[@]}" \
    -e "$base" "$SEARCH_DIR" >/dev/null 2>&1; then
    unused+=("$img")
  fi
done

if [[ ${#unused[@]} -eq 0 ]]; then
  echo "No unused images found."
  exit 0
fi

echo "Found ${#unused[@]} unused image(s):"
for u in "${unused[@]}"; do
  echo " - $u"
done

if [[ "$DELETE" != true ]]; then
  echo "\nDry run: nothing deleted. Re-run with --delete to move unused images to slides/.unused-images-<ts>/"
  exit 0
fi

TS=$(date -u +%Y%m%dT%H%M%SZ)
DEST_DIR="$ROOT_DIR/.unused-images-$TS"
mkdir -p "$DEST_DIR"

echo "Moving ${#unused[@]} files to $DEST_DIR"
for u in "${unused[@]}"; do
  mv -v "$u" "$DEST_DIR/"
done

echo "Done. Files moved to: $DEST_DIR"
