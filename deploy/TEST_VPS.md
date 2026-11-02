# Test VPS Deployment

## Prerequisites
- Ubuntu 22.04+
- Root access
- Python 3.10+

## Install

```bash
git clone https://github.com/mcxzar775/RegionGate.git
cd RegionGate
sudo bash deploy/install-test-vps.sh
```

## Verify

```bash
curl http://127.0.0.1:8000/
# Expect: {"status":"ok","service":"regiongate-control-plane"}
```

## Smoke

```bash
# Login (after bootstrap)
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"changeme"}'
```

Agent runs in dry-run mode by default.
