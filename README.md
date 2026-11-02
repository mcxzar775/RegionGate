# RegionGate

Per-exit isolated network namespaces + VLESS/XHTTP/REALITY edge + control plane.

## Quick start (test VPS)

```bash
git clone https://github.com/mcxzar775/RegionGate.git
cd RegionGate
sudo bash deploy/install-test-vps.sh
curl http://127.0.0.1:8000/
```

## Structure

- `control-plane/` — FastAPI + SQLAlchemy
- `gateway-agent/` — Unix socket privileged agent (dry-run by default)
- `edge/` — Xray config renderer
- `admin/` — Chinese web admin
- `ios/` — SwiftUI + Packet Tunnel skeleton
- `deploy/` — install scripts + compose

## Status

See `docs/STATUS.md`.
