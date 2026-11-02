# RegionGate

自托管 iPhone 地区出口管理系统。

**协议基线（锁定）**: VLESS + XHTTP + REALITY (X25519)  
**出口来源**: VPNGate（每个活动出口运行在独立 Linux network namespace）  
**客户端**: iOS SwiftUI + NetworkExtension Packet Tunnel + libXray  
**控制面**: HTTPS JSON API + SSE  
**管理端**: 响应式中文网页后台  

本文档与 `docs/CLOUD_AUTOMATION_PROJECT_BRIEF.md` 为唯一协议与交付基线。仓库内旧文档或代码与基线冲突时，以基线为准。

## 仓库结构

```text
regiongate/
├── ios/
├── control-plane/
├── admin/
├── edge/
├── gateway-agent/
├── deploy/
├── automation/
└── docs/
```

## 快速开始

```bash
sudo bash deploy/install-test-vps.sh
```

协议基线: VLESS + XHTTP + REALITY (X25519)
