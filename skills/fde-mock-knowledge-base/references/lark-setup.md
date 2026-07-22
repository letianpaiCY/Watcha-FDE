# 飞书 CLI 安装与授权

预检脚本只检查环境，不执行安装或授权。

## missing_node

告知用户需要先安装 Node.js LTS。不要擅自选择操作系统包管理器或修改其环境。

## missing_lark_cli

展示以下官方安装命令并请求确认：

```bash
npx @larksuite/cli@latest install
```

用户确认后执行，再重新运行 `preflight.py`。不要静默安装。

## needs_auth

如果尚未配置应用，在后台运行 `lark-cli config init --new`。命令返回 `verification_url` 或 `console_url` 后，保持 URL 原样，并生成二维码：

```bash
lark-cli auth qrcode "<命令返回的 URL>" --output ./lark-auth-qr.png
```

把原始 URL 和二维码一起交给用户完成配置。

发起最小业务域登录：

```bash
lark-cli auth login --domain docs --domain drive --no-wait --json
```

收到 `verification_url` 后，再为该 URL 生成二维码，把原始 URL 和二维码一起发给用户，并结束当前轮。用户明确回复已授权后，再执行：

```bash
lark-cli auth login --device-code <本次返回的 device_code>
```

只使用本次授权流程返回的 `device_code`；链接过期或流程中断时重新发起授权。不得输出密钥或 Token。

## ready

继续场景脚本。所有云端写入前仍需展示预览并获得一次明确确认。
