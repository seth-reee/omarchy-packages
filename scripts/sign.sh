#!/usr/bin/env bash
set -euo pipefail
export GNUPGHOME
GNUPGHOME=$(mktemp -d)
trap 'gpgconf --kill gpg-agent; rm -rf "$GNUPGHOME"' EXIT
chmod 700 "$GNUPGHOME"
printf '%s' "$REPOSITORY_SIGNING_KEY" | gpg --batch --import
unset REPOSITORY_SIGNING_KEY
repo_dir=${REPOSITORY_ROOT:-/repo}
site_dir=${SITE_DIR:-/site}
fingerprint=$(cat "$repo_dir/keys/fingerprint")
gpg --batch --list-secret-keys "$fingerprint" >/dev/null
for arch in x86_64 aarch64; do
  cd "$site_dir/$arch"
  for package in ./*.pkg.tar.zst; do
    gpg --batch --yes --local-user "$fingerprint" --detach-sign "$package"
    gpg --batch --verify "$package.sig" "$package"
  done
  repo-add --sign --key "$fingerprint" seth-reee.db.tar.gz ./*.pkg.tar.zst
  gpg --batch --verify seth-reee.db.tar.gz.sig seth-reee.db.tar.gz
  # Pages artifacts cannot contain symlinks; pacman needs the .db/.files aliases.
  python - <<'PYTHON'
from pathlib import Path
for path in Path('.').iterdir():
    if path.is_symlink():
        data = path.read_bytes()
        path.unlink()
        path.write_bytes(data)
PYTHON
  sha256sum ./*.pkg.tar.zst ./*.pkg.tar.zst.sig seth-reee.db seth-reee.db.sig > SHA256SUMS
  bsdtar -tf seth-reee.db
 done
