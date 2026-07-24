#!/usr/bin/env python3
"""Build deterministic learner download packages for FDE mock data."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
FIXED_TIME = (2020, 1, 1, 0, 0, 0)


def usage_markdown(title: str, contents: list[str], steps: list[str]) -> str:
    lines = [
        f"# {title}",
        "",
        "> 本包为脱敏模拟材料，不包含标准答案或验收结论。",
        "",
        "## 文件内容",
        "",
    ]
    lines.extend(f"- {item}" for item in contents)
    lines.extend(["", "## 使用方法", ""])
    lines.extend(f"{index}. {step}" for index, step in enumerate(steps, start=1))
    return "\n".join(lines) + "\n"


def write_markdown(destination: Path, content: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content.replace("\r\n", "\n"))


def copy_markdown(source: Path, destination: Path) -> None:
    write_markdown(destination, source.read_text(encoding="utf-8"))


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def build_meeting(directory: Path) -> None:
    source = SKILLS / "fde-mock-meeting-transcripts" / "assets"
    write_markdown(
        directory / "README.md",
        usage_markdown(
            "会议决策与任务跟踪模拟数据使用说明",
            ["5 份企业会议字幕 Markdown 文档"],
            [
                "将 5 个 MD 文件导入为飞书文档。",
                "自行设计决策与行动项提取字段，并从字幕中构建验收表。",
                "不要把普通讨论直接当作正式决定，缺失信息应保留人工确认。",
            ],
        ),
    )
    for path in sorted(source.glob("*.md")):
        copy_markdown(path, directory / path.name)


def build_expense(directory: Path) -> None:
    source = SKILLS / "fde-mock-expense-tickets" / "assets"
    write_markdown(
        directory / "README.md",
        usage_markdown(
            "企业报销预审模拟数据使用说明",
            ["1 份模拟报销制度 Markdown 文档", "200 条报销 Ticket CSV"],
            [
                "阅读报销制度并把 expense_tickets.csv 导入飞书多维表格。",
                "从原始 Ticket 中自行选择样本并标注预期审核结果。",
                "工具只能进行预审提示，不得自动审批、付款或修改金额。",
            ],
        ),
    )
    copy_markdown(source / "expense_policy.md", directory / "expense-policy.md")
    copy_file(source / "expense_tickets.csv", directory / "expense_tickets.csv")


def build_marketing(directory: Path) -> None:
    source = SKILLS / "fde-mock-marketing-assets" / "assets"
    write_markdown(
        directory / "README.md",
        usage_markdown(
            "CHA CUP 营销图片模拟数据使用说明",
            ["1 份 VI 规范 Markdown 文档", "1 条商品资料", "10 条出图任务", "产品母图和透明 Logo"],
            [
                "将 VI 规范导入为飞书文档，把两个 CSV 分别导入多维表格。",
                "把 images 文件夹中的产品图和 Logo 上传到飞书云盘。",
                "自行标注正常出图、停止出图或人工确认，并构建不少于 10 条 Eval。",
            ],
        ),
    )
    copy_markdown(source / "vi_rules.md", directory / "cha-cup-vi-rules.md")
    copy_file(source / "product.csv", directory / "product.csv")
    copy_file(source / "marketing_tasks.csv", directory / "marketing_tasks.csv")
    copy_file(source / "images" / "cha-cup-product.png", directory / "images" / "cha-cup-product.png")
    copy_file(source / "images" / "cha-cup-logo.png", directory / "images" / "cha-cup-logo.png")


def write_deterministic_zip(source_dir: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(source_dir.rglob("*")):
            if not path.is_file():
                continue
            info = zipfile.ZipInfo(path.relative_to(source_dir.parent).as_posix(), FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(
                info,
                path.read_bytes(),
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )
    os.replace(temporary, destination)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    builders = {
        "fde-meeting-data": build_meeting,
        "fde-expense-data": build_expense,
        "fde-cha-cup-marketing-data": build_marketing,
    }
    results: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="watcha-fde-packages-") as temp:
        staging = Path(temp)
        for package_name, builder in builders.items():
            package_dir = staging / package_name
            package_dir.mkdir(parents=True)
            builder(package_dir)
            destination = output_dir / f"{package_name}.zip"
            write_deterministic_zip(package_dir, destination)
            results.append(
                {
                    "name": destination.name,
                    "bytes": destination.stat().st_size,
                    "sha256": sha256(destination),
                }
            )

    print(json.dumps({"status": "success", "packages": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
