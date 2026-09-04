#!/usr/bin/env bash
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: restore.sh BACKUP.tar.gz" >&2
  exit 2
fi
: "${DATABASE_URL:?DATABASE_URL is required}"
: "${ARCHIVE_DIR:?ARCHIVE_DIR is required}"

bundle="$1"
if [ ! -f "$bundle" ]; then
  echo "Backup does not exist: $bundle" >&2
  exit 1
fi
if [ -d "$ARCHIVE_DIR" ] && [ -n "$(find "$ARCHIVE_DIR" -mindepth 1 -maxdepth 1 -print -quit)" ]; then
  echo "ARCHIVE_DIR must be empty before restore: $ARCHIVE_DIR" >&2
  exit 1
fi

work_dir="$(mktemp -d "${TMPDIR:-/tmp}/guiyuan-restore.XXXXXX")"
trap 'rm -rf "$work_dir"' EXIT
tar -xzf "$bundle" -C "$work_dir"
test -f "$work_dir/database.sql"
test -d "$work_dir/archives"

psql_bin="${PSQL_BIN:-psql}"
"$psql_bin" "$DATABASE_URL" -v ON_ERROR_STOP=1 < "$work_dir/database.sql"
mkdir -p "$ARCHIVE_DIR"
cp -R "$work_dir/archives"/. "$ARCHIVE_DIR"/
echo "Restore completed"
