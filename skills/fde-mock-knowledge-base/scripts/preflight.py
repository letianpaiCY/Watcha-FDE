#!/usr/bin/env python3
"""Check prerequisites without changing the user's machine or Feishu data."""

from __future__ import annotations

import json
import os
import shutil
import subprocess


INSTALL_COMMAND = "npx @larksuite/cli@latest install"
LOGIN_COMMAND = "lark-cli auth login --domain docs --domain drive"


def build_runtime_env() -> dict[str, str]:
    env = os.environ.copy()
    if os.name == "posix":
        shells = [path for path in ("/bin/zsh", "/bin/bash", shutil.which("bash")) if path]
        for shell in dict.fromkeys(shells):
            located = subprocess.run(
                [shell, "-lic", "printf '%s' \"$PATH\""],
                capture_output=True,
                text=True,
                check=False,
            )
            if located.returncode == 0 and located.stdout.strip():
                env["PATH"] = located.stdout.strip().splitlines()[-1]
                break
    return env


RUNTIME_ENV = build_runtime_env()


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False, env=RUNTIME_ENV)


def resolve_command(name: str) -> str | None:
    return shutil.which(name, path=RUNTIME_ENV.get("PATH"))


def main() -> int:
    result: dict[str, object] = {
        "ready": False,
        "install_command": INSTALL_COMMAND,
        "login_command": LOGIN_COMMAND,
    }

    lark_cli = resolve_command("lark-cli")
    if not lark_cli:
        npx = resolve_command("npx")
        result.update(
            {
                "status": "missing_lark_cli" if npx else "missing_node",
                "npx_available": bool(npx),
                "message": (
                    "未检测到飞书 CLI。征得用户确认后运行 install_command。"
                    if npx
                    else "未检测到 Node.js/npx。请先安装 Node.js LTS，再重新运行。"
                ),
            }
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    version = run([lark_cli, "--version"])
    if version.returncode != 0:
        result.update(
            {
                "status": "broken_lark_cli",
                "message": "飞书 CLI 已存在但无法运行，请重新安装后再试。",
            }
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    result["version"] = version.stdout.strip()
    auth = run([lark_cli, "auth", "status", "--json", "--verify"])
    if auth.returncode != 0:
        result.update(
            {
                "status": "needs_auth",
                "message": "飞书 CLI 已安装，但尚未完成配置、登录或授权。",
                "configure_command": "lark-cli config init --new",
            }
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    try:
        auth_data = json.loads(auth.stdout)
    except json.JSONDecodeError:
        auth_data = {}

    verified = bool(auth_data.get("verified"))
    identities = auth_data.get("identities", {})
    user = identities.get("user", {}) if isinstance(identities, dict) else {}
    token_status = user.get("tokenStatus") if isinstance(user, dict) else None
    user_ready = verified or token_status in {"valid", "active"}

    if not user_ready:
        result.update(
            {
                "status": "needs_auth",
                "message": "飞书用户身份未通过验证，请完成登录授权。",
            }
        )
    else:
        result.update(
            {
                "ready": True,
                "status": "ready",
                "message": "飞书 CLI 和用户登录状态正常。",
            }
        )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
