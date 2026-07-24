from __future__ import annotations

import csv
import json
import subprocess
import sys
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "fde-mock-marketing-assets"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class MarketingAssetsTest(unittest.TestCase):
    def test_product_data_contains_one_fixed_sku(self) -> None:
        records = read_csv(SKILL / "assets" / "product.csv")
        self.assertEqual(len(records), 1)
        product = records[0]
        self.assertEqual(product["商品ID"], "CHA-CUP-001")
        self.assertEqual(product["SKU"], "CHA-CUP-500-WHITE")
        self.assertEqual(product["商品名称"], "CHA CUP 城市轻量保温杯")
        self.assertEqual(product["颜色"], "雾白")
        self.assertEqual(product["日常价"], "129")
        self.assertEqual(product["最低允许促销价"], "89")

    def test_tasks_cover_raw_edge_cases_without_answers(self) -> None:
        records = read_csv(SKILL / "assets" / "marketing_tasks.csv")
        self.assertEqual(len(records), 10)
        self.assertEqual(len({record["任务ID"] for record in records}), 10)
        forbidden = {"问题标签", "预期结论", "是否通过", "标准答案", "异常类型"}
        self.assertTrue(forbidden.isdisjoint(records[0]))
        self.assertEqual(sum(not record["活动价"] for record in records), 1)
        self.assertEqual(sum(float(record["活动价"]) < 89 for record in records if record["活动价"]), 1)
        self.assertEqual(
            sum(
                record["投放日期"] < record["活动开始日期"]
                or record["投放日期"] > record["活动结束日期"]
                for record in records
            ),
            1,
        )
        self.assertEqual(sum("全网第一" in record["主文案"] for record in records), 1)
        self.assertEqual(sum(record["画布比例"] == "16:9" for record in records), 1)
        self.assertEqual(sum("红色" in record["补充要求"] for record in records), 1)

    def test_vi_rules_are_machine_checkable(self) -> None:
        content = (SKILL / "assets" / "vi_rules.md").read_text(encoding="utf-8")
        for value in (
            "2000×2000",
            "1500×2000",
            "#244638",
            "12%–20%",
            "50%",
            "全网第一",
            "最低允许促销价",
        ):
            self.assertIn(value, content)

    def test_images_match_fixed_asset_contract(self) -> None:
        image_dir = SKILL / "assets" / "images"
        with Image.open(image_dir / "cha-cup-product.png") as product:
            self.assertEqual(product.size, (1254, 1254))
        with Image.open(image_dir / "cha-cup-logo.png") as logo:
            self.assertEqual(logo.mode, "RGBA")
            alpha = logo.getchannel("A")
            corners = (
                alpha.getpixel((0, 0)),
                alpha.getpixel((logo.width - 1, 0)),
                alpha.getpixel((0, logo.height - 1)),
                alpha.getpixel((logo.width - 1, logo.height - 1)),
            )
            self.assertEqual(corners, (0, 0, 0, 0))
            self.assertIsNotNone(alpha.getbbox())
            colors = logo.getcolors(maxcolors=logo.width * logo.height)
            self.assertIsNotNone(colors)
            visible_colors = {pixel[:3] for _, pixel in colors or [] if pixel[3] > 0}
            self.assertEqual(visible_colors, {(0x24, 0x46, 0x38)})

    def test_dry_run_reports_exact_write_scope(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/create_feishu_resources.py", "--dry-run"],
            cwd=SKILL,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["uploads"], 2)
        self.assertEqual(payload["documents"], 1)
        self.assertEqual(payload["bases"], 1)
        self.assertEqual(payload["tables"], 2)
        self.assertEqual(payload["records"], 11)
        self.assertFalse(payload["contains_answer_labels"])

    def test_preflight_requests_docs_drive_and_base(self) -> None:
        content = (SKILL / "scripts" / "preflight.py").read_text(encoding="utf-8")
        login_line = next(
            line for line in content.splitlines() if line.startswith("LOGIN_COMMAND")
        )
        self.assertIn("--domain docs --domain drive --domain base", login_line)


if __name__ == "__main__":
    unittest.main()
