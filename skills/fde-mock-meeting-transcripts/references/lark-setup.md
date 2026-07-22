# 飞书 CLI 安装与授权

预检脚本只检查环境，不执行安装或授权。

## missing_node

告知用户需要先安装 Node.js LTS。不要擅自选择操作系统包管理器或修改其环境。

## missing_lark_cli

展示 `npx @larksuite/cli@latest install` 并请求确认。用户确认后执行，再重新运行 `preflight.py`。不要静默安装。

## needs_auth

未配置时在后台运行 `lark-cli config init --new`。命令返回 URL 后保持原样，运行 `lark-cli auth qrcode "<命令返回的 URL>" --output ./lark-auth-qr.png`，把链接和二维码一起交给用户。随后运行：

```bash
lark-cli auth login --domain docs --domain drive --no-wait --json
```

把 `verification_url` 原样发给用户，同时为该 URL 生成二维码，并结束当前轮；用户回复已授权后，使用本次返回的 `device_code` 完成登录。链接过期或流程中断时重新发起授权，不得输出密钥或 Token。

## ready

继续场景脚本。所有云端写入前仍需展示预览并获得一次明确确认。
