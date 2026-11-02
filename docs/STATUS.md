# RegionGate Status

## Phase 0 - Done
Scaffold, CI, risk checklist.

## Phase 1 - Working on test VPS
- SQLite models, admin bootstrap, login
- Regions, exits, devices, enrollment
- VPNGate sync (parser v3) stores OVPN server-side only
- Idempotency-Key on candidate add
- Audit log on exit add

## Phase 2 - Dry-run path wired
- Agent unix socket + SO_PEERCRED (root)
- Command whitelist + OVPN directive rejection
- create_slot / start_openvpn / test_exit / destroy_slot
- Failed provision rolls the slot back
- Real netns/OpenVPN still behind --privileged (not default)

## Phase 3 - Skeleton
Xray REALITY renderer only. No key generation, no atomic reload yet.

## Not done
- SSE
- Ed25519 config signing
- Admin UI bound to the live API
- Alembic instead of create_all
- Privileged runner
- iOS libXray
