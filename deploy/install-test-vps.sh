#!/usr/bin/env bash
# RegionGate — Test VPS install script (dry-run by default)
#
# Usage (from repo root or any path; script locates repo via itself):
#   sudo bash deploy/install-test-vps.sh
#   sudo bash deploy/install-test-vps.sh --privileged   # needs TUN/OpenVPN; still experimental
#   sudo bash deploy/install-test-vps.sh --smoke-only    # services already installed
#
# Defaults:
#   - REGIONGATE_AGENT_DRY_RUN=1  (no real netns / OpenVPN)
#   - SQLite for control-plane
#   - API on 0.0.0.0:8000
#   - Agent Unix socket /run/regiongate/agent.sock
#
# Does NOT: upload to App Store, change public DNS, write REALITY private keys into git.

set -euo pipefail

PRIVILEGED=0
SMOKE_ONLY=0
SKIP_DEPS=0

for arg in "$@"; do
  case "$arg" in
    --privileged) PRIVILEGED=1 ;;
    --smoke-only) SMOKE_ONLY=1 ;;
    --skip-deps) SKIP_DEPS=1 ;;
    -h|--help)
      sed -n '1,25p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown arg: $arg" >&2
      exit 1
      ;;
  esac
done

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run as root: sudo bash $0" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
INSTALL_ROOT="${REGIONGATE_INSTALL_ROOT:-/opt/regiongate}"
RUN_DIR="/run/regiongate"
DATA_DIR="/var/lib/regiongate"
LOG_DIR="/var/log/regiongate"
ENV_FILE="/etc/regiongate/test.env"

echo "=== RegionGate Test VPS install ==="
echo "REPO_ROOT=$REPO_ROOT"
echo "INSTALL_ROOT=$INSTALL_ROOT"
echo "PRIVILEGED=$PRIVILEGED"
