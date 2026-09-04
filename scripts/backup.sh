#!/usr/bin/env bash
set -eu

: "${DATABASE_URL:?DATABASE_URL is required}"
: "${ARCHIVE_DIR:?ARCHIVE_DIR is required}"
: "${BACKUP_DIR:?BACKUP_DIR is required}"

if [ ! -d "$ARCHIVE_DIR" ]; then
  echo "Archive directory does not exist: $ARCHIVE_DIR" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
work_dir="$(mktemp -d "${TMPDIR:-/tmp}/guiyuan-backup.XXXXXX")"
trap 'rm -rf "$work_dir"' EXIT
mkdir -p "$work_dir/archives"

pg_dump_bin="${PG_DUMP_BIN:-pg_dump}"
"$pg_dump_bin" "$DATABASE_URL" > "$work_dir/database.sql"
cp -R "$ARCHIVE_DIR"/. "$work_dir/archives"/

bundle_files=(database.sql archives)
if [ -n "${ENV_FILE:-}" ] && [ -f "$ENV_FILE" ]; then
  cp "$ENV_FILE" "$work_dir/environment.env"
  bundle_files+=(environment.env)
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
bundle="$BACKUP_DIR/guiyuan-backup-$timestamp.tar.gz"
tar -czf "$bundle" -C "$work_dir" "${bundle_files[@]}"
echo "$bundle"
