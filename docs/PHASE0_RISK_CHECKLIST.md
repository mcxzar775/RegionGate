# Phase 0 Risk Checklist

- [ ] Agent socket permissions (SO_PEERCRED)
- [ ] Dry-run default on test VPS
- [ ] No real OpenVPN until explicit --privileged
- [ ] VPNGate feed is public HTTPS only
- [ ] Dangerous OVPN directives rejected
- [ ] Secrets not in git
- [ ] Bootstrap admin password rotated after first login
- [ ] Network namespaces isolated per exit
