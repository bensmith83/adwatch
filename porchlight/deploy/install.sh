#!/usr/bin/env bash
# Install or upgrade Porchlight on a Raspberry Pi (64-bit Raspberry Pi OS, Bookworm or later).
#
# Copy this folder to the Pi with the parser binary at bin/linux-aarch64/ble-parse
# and its fields table at data/persistent_fields.json (both are supplied
# separately; see README), then run this as root from the copy:
#
#   rsync -a --exclude .git --exclude .venv --exclude parser/.build* ./ pi@porch.local:porchlight/
#   ssh pi@porch.local 'cd porchlight && sudo deploy/install.sh'
#
# It never touches an existing /etc/porchlight/config.toml or /var/lib/porchlight.
set -euo pipefail

src="$(cd "$(dirname "$0")/.." && pwd)"
opt=/opt/porchlight
etc=/etc/porchlight
state=/var/lib/porchlight

[ "$(id -u)" = 0 ] || { echo "run as root (sudo)" >&2; exit 1; }
[ "$(uname -m)" = aarch64 ] || { echo "needs 64-bit ARM (aarch64); this is $(uname -m)" >&2; exit 1; }
bin="$src/bin/linux-aarch64/ble-parse"
fields="$src/data/persistent_fields.json"
[ -x "$bin" ] || { echo "missing $bin: the parser binary is supplied separately (see README)" >&2; exit 1; }
[ -f "$fields" ] || { echo "missing $fields: the fields table comes with the parser (see README)" >&2; exit 1; }
python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))' || { echo "needs Python 3.11+" >&2; exit 1; }

missing=()
python3 -c 'import venv, ensurepip' 2>/dev/null || missing+=(python3-venv)
command -v bluetoothctl >/dev/null || missing+=(bluez)
if [ ${#missing[@]} -gt 0 ]; then
    apt-get update -q && apt-get install -y -q "${missing[@]}"
fi

id porchlight >/dev/null 2>&1 || useradd --system --no-create-home --home-dir "$state" --shell /usr/sbin/nologin porchlight
usermod -a -G bluetooth porchlight

install -d -m 0755 "$opt" "$opt/bin" "$opt/data" "$opt/src"
install -m 0755 "$bin" "$opt/bin/ble-parse"
install -m 0644 "$fields" "$opt/data/"
install -m 0644 "$src/README.md" "$opt/"
rm -rf "$opt/src"
install -d -m 0755 "$opt/src"
cp -r "$src/porchlight" "$src/pyproject.toml" "$opt/src/"
find "$opt/src" -name __pycache__ -prune -exec rm -rf {} +

[ -d "$opt/venv" ] || python3 -m venv "$opt/venv"
"$opt/venv/bin/pip" install -q --upgrade pip
"$opt/venv/bin/pip" install -q "$opt/src"
ln -sf "$opt/venv/bin/porchlight" /usr/local/bin/porchlight

install -d -m 0755 "$etc"
if [ ! -f "$etc/config.toml" ]; then
    install -m 0644 "$src/deploy/config.example.toml" "$etc/config.toml"
    echo "wrote $etc/config.toml (defaults: manual arming, page on 127.0.0.1:8080)"
fi
install -d -m 0700 -o porchlight -g porchlight "$state"

echo "parser: $("$opt/bin/ble-parse" --info | tr '\n' ' ')"
porchlight selftest --config "$etc/config.toml"

install -m 0644 "$src/deploy/porchlight.service" /etc/systemd/system/porchlight.service
systemctl daemon-reload
systemctl enable porchlight.service
systemctl restart porchlight.service
sleep 3
systemctl --no-pager --lines=5 status porchlight.service || true
echo
echo "Installed. Logs: journalctl -u porchlight -f    Units near now: porchlight status"
echo "Page: ssh -L 8080:localhost:8080 <pi> then http://localhost:8080/ (or set web.listen and web.token)"
