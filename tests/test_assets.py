from __future__ import annotations

import csv
import importlib.util
import json
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


class KnowledgeAssetsTest(unittest.TestCase):
    def test_each_industry_has_five_structured_documents(self) -> None:
        base = SKILLS / "fde-mock-knowledge-base" / "assets"
        for industry in ("manufacturing", "beauty-retail", "pharma"):
            documents = sorted((base / industry).glob("*.md"))
            self.assertEqual(len(documents), 5, industry)
            for document in documents:
                content = document.read_text(encoding="utf-8")
                self.assertTrue(content.startswith("# "))
                for heading in ("## 文档信息", "## 例外与人工升级", "## 不适用范围", "## 公开来源"):
                    self.assertIn(heading, content, document.name)
                self.assertIn("https://", content)


class MeetingAssetsTest(unittest.TestCase):
    def test_five_transcripts_contain_timestamps_and_ambiguity(self) -> None:
        base = SKILLS / "fde-mock-meeting-transcripts" / "assets"
        documents = sorted(base.glob("*.md"))
        self.assertEqual(len(documents), 5)
        for document in documents:
            content = document.read_text(encoding="utf-8")
            timestamps = re.findall(r"\[\d{2}:\d{2}:\d{2}\]", content)
            self.assertGreaterEqual(len(timestamps), 25, document.name)
            self.assertRegex(content, r"待确认|不能.*承诺|不作为.*承诺")
            self.assertIn("脱敏仿真", content)


class ExpenseAssetsTest(unittest.TestCase):
    def test_ticket_csv_has_200_unlabelled_records(self) -> None:
        path = SKILLS / "fde-mock-expense-tickets" / "assets" / "expense_tickets.csv"
        with path.open(encoding="utf-8-sig", newline="") as handle:
            records = list(csv.DictReader(handle))
        self.assertEqual(len(records), 200)
        self.assertEqual(len({record["Ticket ID"] for record in records}), 200)
        forbidden = {"问题标签", "预期结论", "是否通过", "标准答案"}
        self.assertTrue(forbidden.isdisjoint(records[0]))
        self.assertGreater(sum(not record["发票号码"] for record in records), 0)
        self.assertGreater(sum(record["预算编码"] == "UNKNOWN-001" for record in records), 0)

    def test_base_field_verification_rejects_incomplete_schema(self) -> None:
        script = (
            SKILLS
            / "fde-mock-expense-tickets"
            / "scripts"
            / "create_feishu_resources.py"
        )
        spec = importlib.util.spec_from_file_location("expense_resources", script)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        expected = [field["name"] for field in module.FIELD_SCHEMA]
        original = module.run_lark
        try:
            module.run_lark = lambda *_args, **_kwargs: {
                "data": {"items": [{"name": name} for name in expected]}
            }
            self.assertEqual(module.verify_fields("app_test", expected), len(expected))

            module.run_lark = lambda *_args, **_kwargs: {
                "data": {"items": [{"name": name} for name in expected[:-1]]}
            }
            with self.assertRaisesRegex(RuntimeError, "missing"):
                module.verify_fields("app_test", expected)
        finally:
            module.run_lark = original


class DryRunTest(unittest.TestCase):
    def run_json(self, cwd: Path, *args: str) -> dict[str, object]:
        completed = subprocess.run(
            ["python3", *args], cwd=cwd, capture_output=True, text=True, check=False
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def test_knowledge_preview(self) -> None:
        skill = SKILLS / "fde-mock-knowledge-base"
        payload = self.run_json(
            skill, "scripts/create_feishu_docs.py", "--industry", "pharma", "--dry-run"
        )
        self.assertEqual(payload["writes"], 6)
        self.assertEqual(len(payload["documents"]), 5)

    def test_meeting_preview(self) -> None:
        skill = SKILLS / "fde-mock-meeting-transcripts"
        payload = self.run_json(skill, "scripts/create_feishu_docs.py", "--dry-run")
        self.assertEqual(payload["writes"], 6)
        self.assertEqual(len(payload["documents"]), 5)

    def test_expense_preview(self) -> None:
        skill = SKILLS / "fde-mock-expense-tickets"
        payload = self.run_json(skill, "scripts/create_feishu_resources.py", "--dry-run")
        self.assertEqual(payload["records"], 200)
        self.assertFalse(payload["contains_answer_labels"])

    def test_preflight_uses_scenario_specific_domains(self) -> None:
        for skill_name, needs_base in (
            ("fde-mock-knowledge-base", False),
            ("fde-mock-meeting-transcripts", False),
            ("fde-mock-expense-tickets", True),
        ):
            content = (SKILLS / skill_name / "scripts" / "preflight.py").read_text(
                encoding="utf-8"
            )
            login_line = next(
                line for line in content.splitlines() if line.startswith("LOGIN_COMMAND")
            )
            self.assertIn("--domain docs --domain drive", login_line)
            self.assertEqual("--domain base" in login_line, needs_base, skill_name)


if __name__ == "__main__":
    unittest.main()
