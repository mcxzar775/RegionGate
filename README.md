# RegionGate

Per-exit isolated network namespaces + VLESS/XHTTP/REALITY edge + control plane.

## Current Status (Test VPS)

- Control plane running on `:8000`
- Admin login working: `admin` / `changeme`
- SQLite database
- Dry-run Agent skeleton ready

## Quick start

```bash
git clone https://github.com/mcxzar775/RegionGate.git
cd RegionGate
sudo bash deploy/install-test-vps.sh
curl http://127.0.0.1:8000/
```

## Login

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"changeme"}'
```

## Structure

- `control-plane/` — FastAPI + SQLAlchemy
- `gateway-agent/` — Unix socket privileged agent (dry-run by default)
- `edge/` — Xray config renderer
- `admin/` — Chinese web admin skeleton
- `ios/` — SwiftUI + Packet Tunnel skeleton
- `deploy/` — install scripts + compose

## Next

See `docs/STATUS.md`.
