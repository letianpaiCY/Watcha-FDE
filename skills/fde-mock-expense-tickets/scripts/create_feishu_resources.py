#!/usr/bin/env python3
"""Create the mock expense policy document and a 200-row Feishu Base."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
POLICY_PATH = SKILL_DIR / "assets" / "expense_policy.md"
TICKETS_PATH = SKILL_DIR / "assets" / "expense_tickets.csv"
TABLE_NAME = "报销 Ticket"

FIELD_SCHEMA = [
    {"name": "Ticket ID", "type": "text"},
    {"name": "员工编号", "type": "text"},
    {"name": "部门", "type": "text"},
    {"name": "岗位等级", "type": "text"},
    {"name": "费用类型", "type": "text"},
    {"name": "金额", "type": "number"},
    {"name": "城市", "type": "text"},
    {"name": "城市等级", "type": "text"},
    {"name": "费用日期", "type": "text"},
    {"name": "出差开始日期", "type": "text"},
    {"name": "出差结束日期", "type": "text"},
    {"name": "商户", "type": "text"},
    {"name": "发票号码", "type": "text"},
    {"name": "票据状态", "type": "text"},
    {"name": "审批状态", "type": "text"},
    {"name": "预算编码", "type": "text"},
    {"name": "用途说明", "type": "text"},
]


def build_runtime_env() -> dict[str, str]:
    env = os.environ.copy()
    if os.name == "posix":
        for shell in dict.fromkeys(path for path in ("/bin/zsh", "/bin/bash", shutil.which("bash")) if path):
            located = subprocess.run(
                [shell, "-lic", "printf '%s' \"$PATH\""], capture_output=True, text=True, check=False
            )
            if located.returncode == 0 and located.stdout.strip():
                env["PATH"] = located.stdout.strip().splitlines()[-1]
                break
    return env


RUNTIME_ENV = build_runtime_env()


def run_lark(args: list[str], stdin: str | None = None) -> dict[str, Any]:
    completed = subprocess.run(
        ["lark-cli", *args],
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
        env=RUNTIME_ENV,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(message or f"lark-cli exited with {completed.returncode}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("lark-cli returned non-JSON output") from exc


def find_value(value: Any, keys: tuple[str, ...]) -> Any:
    if isinstance(value, dict):
        for key in keys:
            child = value.get(key)
            if child:
                return child
        for child in value.values():
            found = find_value(child, keys)
            if found:
                return found
    if isinstance(value, list):
        for child in value:
            found = find_value(child, keys)
            if found:
                return found
    return None


def read_policy() -> tuple[str, str]:
    lines = POLICY_PATH.read_text(encoding="utf-8").splitlines()
    if not lines or not lines[0].startswith("# "):
        raise ValueError("expense_policy.md must start with '# <title>'")
    return lines[0][2:].strip(), "\n".join(lines[1:]).strip() + "\n"


def read_tickets() -> tuple[list[str], list[list[object]]]:
    with TICKETS_PATH.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows: list[list[object]] = []
        for record in reader:
            row: list[object] = []
            for field in fields:
                value: object = record[field]
                if field == "金额":
                    value = float(record[field])
                row.append(value)
            rows.append(row)
    if len(rows) != 200:
        raise ValueError(f"expected 200 tickets, found {len(rows)}")
    return fields, rows


def create_policy(title: str, body: str) -> dict[str, str]:
    payload = run_lark(
        [
            "docs",
            "+create",
            "--as",
            "user",
            "--parent-position",
            "my_library",
            "--title",
            title,
            "--doc-format",
            "markdown",
            "--content",
            "-",
            "--format",
            "json",
        ],
        stdin=body,
    )
    url = find_value(payload, ("url",))
    token = find_value(payload, ("document_id", "doc_token", "token"))
    if not url and token:
        url = f"https://feishu.cn/docx/{token}"
    if not url:
        raise RuntimeError("policy document created but URL was not returned")
    return {"title": title, "url": str(url), "token": str(token or "")}


def create_base(name: str) -> tuple[str, str]:
    payload = run_lark(
        [
            "base",
            "+base-create",
            "--as",
            "user",
            "--name",
            name,
            "--table-name",
            TABLE_NAME,
            "--fields",
            json.dumps(FIELD_SCHEMA, ensure_ascii=False),
            "--time-zone",
            "Asia/Shanghai",
            "--format",
            "json",
        ]
    )
    token = find_value(payload, ("base_token", "app_token"))
    url = find_value(payload, ("url",))
    if not token:
        raise RuntimeError("Base created but base_token was not returned")
    if not url:
        url = f"https://feishu.cn/base/{token}"
    return str(token), str(url)


def verify_fields(base_token: str, expected_fields: list[str]) -> int:
    payload = run_lark(
        [
            "base",
            "+field-list",
            "--as",
            "user",
            "--base-token",
            base_token,
            "--table-id",
            TABLE_NAME,
            "--limit",
            "200",
            "--format",
            "json",
        ]
    )
    remote_fields = find_value(payload, ("fields", "items"))
    if not isinstance(remote_fields, list):
        raise RuntimeError("Base created but its field schema could not be read back")
    observed = {
        str(field.get("name") or field.get("field_name"))
        for field in remote_fields
        if isinstance(field, dict) and (field.get("name") or field.get("field_name"))
    }
    missing = [field for field in expected_fields if field not in observed]
    if missing:
        raise RuntimeError(f"Base field verification failed; missing: {', '.join(missing)}")
    return len(expected_fields)


def create_records(base_token: str, fields: list[str], rows: list[list[object]]) -> None:
    for start in range(0, len(rows), 100):
        batch = rows[start : start + 100]
        run_lark(
            [
                "base",
                "+record-batch-create",
                "--as",
                "user",
                "--base-token",
                base_token,
                "--table-id",
                TABLE_NAME,
                "--json",
                json.dumps({"fields": fields, "rows": batch}, ensure_ascii=False),
                "--format",
                "json",
            ]
        )


def verify_records(base_token: str) -> int:
    payload = run_lark(
        [
            "base",
            "+record-list",
            "--as",
            "user",
            "--base-token",
            base_token,
            "--table-id",
            TABLE_NAME,
            "--limit",
            "200",
            "--format",
            "json",
        ]
    )
    records = find_value(payload, ("records", "items"))
    return len(records) if isinstance(records, list) else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-name", help="Optional run label")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true", help="Confirm Feishu writes")
    args = parser.parse_args()

    policy_title, policy_body = read_policy()
    fields, rows = read_tickets()
    batch = args.batch_name or dt.datetime.now().strftime("%Y%m%d-%H%M")
    preview = {
        "batch": batch,
        "policy_document": policy_title,
        "base_name": f"FDE Mock 报销 Ticket {batch}",
        "records": len(rows),
        "contains_answer_labels": False,
    }
    if args.dry_run or not args.yes:
        preview["status"] = "preview"
        preview["next_command"] = "python3 scripts/create_feishu_resources.py --yes"
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        return 0 if args.dry_run else 2

    created: dict[str, object] = {}
    try:
        policy = create_policy(f"[FDE Mock·报销·{batch}] {policy_title}", policy_body)
        created["policy"] = policy
        base_token, base_url = create_base(f"FDE Mock 报销 Ticket {batch}")
        created["base"] = {"url": base_url, "base_token": base_token}
        created["verified_fields"] = verify_fields(base_token, fields)
        create_records(base_token, fields, rows)
        count = verify_records(base_token)
        if count != 200:
            raise RuntimeError(f"verification expected 200 records, found {count}")
        created["verified_records"] = count
    except Exception as exc:
        print(
            json.dumps(
                {"status": "partial_failure", "error": str(exc), "created": created},
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1

    print(json.dumps({"status": "success", "created": created}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
