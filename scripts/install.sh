#!/usr/bin/env bash
set -euo pipefail
if (( EUID != 0 )); then
  echo 'Run this installer with sudo in your terminal.' >&2
  exit 1
fi
case "$(uname -m)" in x86_64|aarch64) ;; *) echo 'Unsupported architecture' >&2; exit 1 ;; esac
fingerprint=186C035DEE6A26BD035AB1D3319FE7C0F23D8AE5
temporary=$(mktemp -d)
trap 'rm -rf "$temporary"' EXIT
curl -fL --retry 3 https://seth-reee.github.io/omarchy-packages/seth-reee.asc -o "$temporary/key.asc"
actual=$(gpg --batch --show-keys --with-colons "$temporary/key.asc" | awk -F: '$1 == "fpr" {print $10; exit}')
[[ "$actual" == "$fingerprint" ]] || { echo 'Signing key fingerprint mismatch' >&2; exit 1; }
pacman-key --add "$temporary/key.asc"
pacman-key --lsign-key "$fingerprint"
# Validate the live signed database without refreshing system repositories or
# installing anything. The next Omarchy Update performs the normal full refresh.
mkdir -p "$temporary/db" "$temporary/cache"
cat > "$temporary/validation.conf" <<'VALIDATION'
[options]
Architecture = auto
SigLevel = Required
[seth-reee]
SigLevel = Required
Server = https://seth-reee.github.io/omarchy-packages/$arch
VALIDATION
pacman --config "$temporary/validation.conf" --dbpath "$temporary/db" \
  --cachedir "$temporary/cache" --logfile "$temporary/pacman.log" \
  --gpgdir /etc/pacman.d/gnupg -Sy
pacman --config "$temporary/validation.conf" --dbpath "$temporary/db" -Sl seth-reee
config=/etc/pacman.d/seth-reee.conf
if [[ -f "$config" ]]; then cp -a "$config" "$config.backup-$(date +%Y%m%d%H%M%S)"; fi
cat > "$config" <<'CONFIG'
[seth-reee]
SigLevel = Required
Server = https://seth-reee.github.io/omarchy-packages/$arch
CONFIG
if ! grep -Fxq 'Include = /etc/pacman.d/seth-reee.conf' /etc/pacman.conf; then
  cp -a /etc/pacman.conf "/etc/pacman.conf.before-seth-reee-$(date +%Y%m%d%H%M%S)"
  printf '\n# Signed Seth Reee application packages\nInclude = /etc/pacman.d/seth-reee.conf\n' >> /etc/pacman.conf
fi
pacman-conf --repo seth-reee Server
printf '\nRepository configured. Run omarchy update for normal package upgrades.\n'
