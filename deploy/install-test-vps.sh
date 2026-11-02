#!/usr/bin/env bash
# RegionGate — Test VPS install script (dry-run by default)
#
# Usage:
#   sudo bash deploy/install-test-vps.sh
#   sudo bash deploy/install-test-vps.sh --privileged
#   sudo bash deploy/install-test-vps.sh --smoke-only
#
# Defaults to dry-run Agent (no real netns/OpenVPN).

set -euo pipefail

PRIVILEGED=0
SMOKE_ONLY=0

for arg in "$@"; do
  case "$arg" in
    --privileged) PRIVILEGED=1 ;;
    --smoke-only) SMOKE_ONLY=1 ;;
    -h|--help) sed -n '1,12p' "$0"; exit 0 ;;
    *) echo "Unknown arg: $arg" >&2; exit 1 ;;
  esac
done

if [[ $EUID -ne 0 ]]; then
  echo "Please run as root" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTALL_ROOT="${REGIONGATE_INSTALL_ROOT:-/opt/regiongate}"

echo "=== RegionGate Test VPS install ==="
echo "REPO=$REPO_ROOT  INSTALL=$INSTALL_ROOT  PRIVILEGED=$PRIVILEGED"

# Install required system packages
echo "=== Installing system dependencies ==="
apt-get update -qq
apt-get install -y -qq python3-venv python3-pip python3-dev build-essential || true

if [[ $SMOKE_ONLY -eq 0 ]]; then
  mkdir -p /opt/regiongate /run/regiongate /var/lib/regiongate /etc/regiongate
  chmod 755 /var/lib/regiongate
  cp -a "$REPO_ROOT/." /opt/regiongate/
  cd /opt/regiongate

  # Python venv for control-plane
  python3 -m venv /opt/regiongate/.venv
  /opt/regiongate/.venv/bin/pip install -q --upgrade pip
  /opt/regiongate/.venv/bin/pip install -q -e control-plane/ || true
  /opt/regiongate/.venv/bin/pip install -q -e gateway-agent/ || true

  cat > /etc/regiongate/test.env <<EOF
REGIONGATE_AGENT_DRY_RUN=1
REGIONGATE_DATABASE_URL=sqlite+aiosqlite:////var/lib/regiongate/regiongate.db
REGIONGATE_ADMIN_BOOTSTRAP_PASSWORD=changeme
EOF

  # systemd units (minimal)
  cat > /etc/systemd/system/regiongate-api.service <<EOF
[Unit]
Description=RegionGate Control Plane
After=network.target

[Service]
EnvironmentFile=/etc/regiongate/test.env
WorkingDirectory=/opt/regiongate/control-plane
ExecStart=/opt/regiongate/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

  systemctl daemon-reload
  systemctl enable --now regiongate-api || true
fi

echo "=== Done. API should be on :8000 ==="
echo "curl http://127.0.0.1:8000/"
