# 测试 VPS 部署

## 一键安装（默认 dry-run）

```bash
sudo bash deploy/install-test-vps.sh
```

默认 dry-run：API + Agent，不建真实 netns。

安装后：
- 密码：sudo grep ADMIN_BOOTSTRAP /etc/regiongate/test.env
- API：http://<VPS-IP>:8000/docs
- smoke：sudo bash /opt/regiongate/deploy/install-test-vps.sh --smoke-only
