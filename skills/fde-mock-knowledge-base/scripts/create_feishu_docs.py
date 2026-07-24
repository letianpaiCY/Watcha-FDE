#!/usr/bin/env python3
"""Create the beauty retail knowledge pack as Feishu documents."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
INDUSTRY_NAME = "美妆零售"
ASSET_DIR = SKILL_DIR / "assets" / "beauty-retail"


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


def find_value(value: Any, keys: set[str]) -> Any:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in keys and child:
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


def read_asset(path: Path) -> tuple[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or not lines[0].startswith("# "):
        raise ValueError(f"{path.name} must start with '# <title>'")
    title = lines[0][2:].strip()
    body = "\n".join(lines[1:]).strip() + "\n"
    return title, body


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
    url = find_value(payload, {"url"})
    token = find_value(payload, {"document_id", "doc_token", "token"})
    if not url and token:
        url = f"https://feishu.cn/docx/{token}"
    if not url:
        raise RuntimeError(f"document created but URL was not returned: {title}")
    return {"title": title, "url": str(url), "token": str(token or "")}


def verify_document(url: str) -> bool:
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
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-name", help="Optional run label")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true", help="Confirm Feishu writes")
    args = parser.parse_args()

    assets = sorted(ASSET_DIR.glob("*.md"))
    if len(assets) != 5:
        raise SystemExit(f"expected 5 documents in {ASSET_DIR}, found {len(assets)}")
    documents = [read_asset(path) for path in assets]
    batch = args.batch_name or dt.datetime.now().strftime("%Y%m%d-%H%M")

    preview = {
        "industry": INDUSTRY_NAME,
        "batch": batch,
        "documents": [title for title, _ in documents],
        "writes": 6,
    }
    if args.dry_run or not args.yes:
        preview["status"] = "preview"
        preview["next_command"] = "python3 scripts/create_feishu_docs.py --yes"
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        return 0 if args.dry_run else 2

    created: list[dict[str, str]] = []
    try:
        for title, body in documents:
            final_title = f"[FDE Mock·{INDUSTRY_NAME}·{batch}] {title}"
            created.append(create_document(final_title, body))

        index_lines = [
            f"本批次包含 5 篇{INDUSTRY_NAME}脱敏模拟企业知识文档。",
            "",
            "这些材料只用于 FDE 共学营项目实践，不代表真实企业制度或专业意见。",
            "",
            "## 文档目录",
            "",
        ]
        index_lines.extend(f"- [{item['title']}]({item['url']})" for item in created)
        index = create_document(
            f"[FDE Mock·{INDUSTRY_NAME}·{batch}] 知识库目录",
            "\n".join(index_lines) + "\n",
        )
        created.append(index)
        for item in created:
            item["verified"] = str(verify_document(item["url"])).lower()
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

    print(
        json.dumps(
            {"status": "success", "industry": INDUSTRY_NAME, "created": created},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
