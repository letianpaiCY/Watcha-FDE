#!/usr/bin/env python3
"""Create CHA CUP mock marketing resources in Feishu."""

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
VI_PATH = SKILL_DIR / "assets" / "vi_rules.md"
PRODUCT_PATH = SKILL_DIR / "assets" / "product.csv"
TASK_PATH = SKILL_DIR / "assets" / "marketing_tasks.csv"
PRODUCT_IMAGE = Path("assets/images/cha-cup-product.png")
LOGO_IMAGE = Path("assets/images/cha-cup-logo.png")
PRODUCT_TABLE = "商品资料"
TASK_TABLE = "出图任务"

PRODUCT_SCHEMA = [
    {"name": "商品ID", "type": "text"},
    {"name": "商品名称", "type": "text"},
    {"name": "SKU", "type": "text"},
    {"name": "容量", "type": "text"},
    {"name": "颜色", "type": "text"},
    {"name": "日常价", "type": "number"},
    {"name": "最低允许促销价", "type": "number"},
    {"name": "核心卖点", "type": "text"},
    {"name": "产品图文件名", "type": "text"},
    {"name": "Logo文件名", "type": "text"},
    {"name": "产品图链接", "type": "text", "style": {"type": "url"}},
    {"name": "Logo链接", "type": "text", "style": {"type": "url"}},
]

TASK_SCHEMA = [
    {"name": "任务ID", "type": "text"},
    {"name": "图片类型", "type": "text"},
    {"name": "画布比例", "type": "text"},
    {"name": "投放日期", "type": "text"},
    {"name": "活动名称", "type": "text"},
    {"name": "活动价", "type": "number"},
    {"name": "活动开始日期", "type": "text"},
    {"name": "活动结束日期", "type": "text"},
    {"name": "主文案", "type": "text"},
    {"name": "补充要求", "type": "text"},
]


def build_runtime_env() -> dict[str, str]:
    env = os.environ.copy()
    if os.name == "posix":
        shells = dict.fromkeys(
            path for path in ("/bin/zsh", "/bin/bash", shutil.which("bash")) if path
        )
        for shell in shells:
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


def run_lark(args: list[str], stdin: str | None = None) -> dict[str, Any]:
    completed = subprocess.run(
        ["lark-cli", *args],
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
        cwd=SKILL_DIR,
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


def read_markdown(path: Path) -> tuple[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or not lines[0].startswith("# "):
        raise ValueError(f"{path.name} must start with '# <title>'")
    return lines[0][2:].strip(), "\n".join(lines[1:]).strip() + "\n"


def read_csv(path: Path) -> tuple[list[str], list[list[object]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows: list[list[object]] = []
        for record in reader:
            row: list[object] = []
            for field in fields:
                value: object = record[field]
                if field in {"日常价", "最低允许促销价", "活动价"}:
                    value = float(record[field]) if record[field] else None
                row.append(value)
            rows.append(row)
    return fields, rows


def upload_file(path: Path, name: str) -> dict[str, str]:
    payload = run_lark(
        [
            "drive",
            "+upload",
            "--as",
            "user",
            "--file",
            path.as_posix(),
            "--name",
            name,
            "--format",
            "json",
        ]
    )
    token = find_value(payload, ("file_token", "token"))
    url = find_value(payload, ("url", "web_url"))
    if not token:
        raise RuntimeError(f"file uploaded but token was not returned: {path.name}")
    if not url:
        url = f"https://feishu.cn/file/{token}"
    return {"name": name, "url": str(url), "file_token": str(token)}


def create_document(title: str, body: str) -> dict[str, str]:
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
        raise RuntimeError("VI document created but URL was not returned")
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
            PRODUCT_TABLE,
            "--fields",
            json.dumps(PRODUCT_SCHEMA, ensure_ascii=False),
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


def create_table(base_token: str, name: str, schema: list[dict[str, Any]]) -> None:
    run_lark(
        [
            "base",
            "+table-create",
            "--as",
            "user",
            "--base-token",
            base_token,
            "--name",
            name,
            "--fields",
            json.dumps(schema, ensure_ascii=False),
            "--format",
            "json",
        ]
    )


def verify_fields(base_token: str, table: str, expected: list[str]) -> int:
    payload = run_lark(
        [
            "base",
            "+field-list",
            "--as",
            "user",
            "--base-token",
            base_token,
            "--table-id",
            table,
            "--limit",
            "200",
            "--format",
            "json",
        ]
    )
    remote_fields = find_value(payload, ("fields", "items"))
    if not isinstance(remote_fields, list):
        raise RuntimeError(f"field schema could not be read back: {table}")
    observed = {
        str(field.get("name") or field.get("field_name"))
        for field in remote_fields
        if isinstance(field, dict) and (field.get("name") or field.get("field_name"))
    }
    missing = [field for field in expected if field not in observed]
    if missing:
        raise RuntimeError(f"{table} field verification failed; missing: {', '.join(missing)}")
    return len(expected)


def create_records(
    base_token: str, table: str, fields: list[str], rows: list[list[object]]
) -> None:
    run_lark(
        [
            "base",
            "+record-batch-create",
            "--as",
            "user",
            "--base-token",
            base_token,
            "--table-id",
            table,
            "--json",
            json.dumps({"fields": fields, "rows": rows}, ensure_ascii=False),
            "--format",
            "json",
        ]
    )


def verify_records(base_token: str, table: str) -> int:
    payload = run_lark(
        [
            "base",
            "+record-list",
            "--as",
            "user",
            "--base-token",
            base_token,
            "--table-id",
            table,
            "--limit",
            "200",
            "--format",
            "json",
        ]
    )
    records = find_value(payload, ("records", "items"))
    return len(records) if isinstance(records, list) else 0


def verify_document(url: str) -> None:
    run_lark(
        [
            "docs",
            "+fetch",
            "--as",
            "user",
            "--doc",
            url,
            "--scope",
            "outline",
            "--format",
            "json",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-name", help="Optional run label")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true", help="Confirm Feishu writes")
    args = parser.parse_args()

    vi_title, vi_body = read_markdown(VI_PATH)
    product_fields, product_rows = read_csv(PRODUCT_PATH)
    task_fields, task_rows = read_csv(TASK_PATH)
    if len(product_rows) != 1:
        raise SystemExit(f"expected 1 product, found {len(product_rows)}")
    if len(task_rows) != 10:
        raise SystemExit(f"expected 10 tasks, found {len(task_rows)}")

    batch = args.batch_name or dt.datetime.now().strftime("%Y%m%d-%H%M")
    preview = {
        "batch": batch,
        "uploads": 2,
        "documents": 1,
        "bases": 1,
        "tables": 2,
        "records": 11,
        "contains_answer_labels": False,
    }
    if args.dry_run or not args.yes:
        preview["status"] = "preview"
        preview["next_command"] = "python3 scripts/create_feishu_resources.py --yes"
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        return 0 if args.dry_run else 2

    created: dict[str, object] = {}
    try:
        product_image = upload_file(
            PRODUCT_IMAGE, f"[FDE Mock·CHA CUP·{batch}] cha-cup-product.png"
        )
        logo_image = upload_file(LOGO_IMAGE, f"[FDE Mock·CHA CUP·{batch}] cha-cup-logo.png")
        created["files"] = [product_image, logo_image]

        linked_body = (
            vi_body
            + "\n## 素材链接\n\n"
            + f"- [产品母图]({product_image['url']})\n"
            + f"- [透明 Logo]({logo_image['url']})\n"
        )
        document = create_document(f"[FDE Mock·CHA CUP·{batch}] {vi_title}", linked_body)
        created["document"] = document

        base_token, base_url = create_base(f"FDE Mock CHA CUP 营销素材 {batch}")
        created["base"] = {"url": base_url, "base_token": base_token}

        product_write_fields = product_fields + ["产品图链接", "Logo链接"]
        product_write_rows = [
            product_rows[0] + [product_image["url"], logo_image["url"]]
        ]
        created["verified_product_fields"] = verify_fields(
            base_token, PRODUCT_TABLE, product_write_fields
        )
        create_records(base_token, PRODUCT_TABLE, product_write_fields, product_write_rows)

        create_table(base_token, TASK_TABLE, TASK_SCHEMA)
        created["verified_task_fields"] = verify_fields(
            base_token, TASK_TABLE, task_fields
        )
        create_records(base_token, TASK_TABLE, task_fields, task_rows)

        product_count = verify_records(base_token, PRODUCT_TABLE)
        task_count = verify_records(base_token, TASK_TABLE)
        if product_count != 1 or task_count != 10:
            raise RuntimeError(
                f"verification expected 1 product and 10 tasks, found "
                f"{product_count} and {task_count}"
            )
        created["verified_records"] = {
            PRODUCT_TABLE: product_count,
            TASK_TABLE: task_count,
        }
        verify_document(document["url"])
        created["document_verified"] = True
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
