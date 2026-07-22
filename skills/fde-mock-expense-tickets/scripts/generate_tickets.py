#!/usr/bin/env python3
"""Generate deterministic mock expense tickets without answer labels."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import random
from pathlib import Path


FIELDS = [
    "Ticket ID",
    "员工编号",
    "部门",
    "岗位等级",
    "费用类型",
    "金额",
    "城市",
    "城市等级",
    "费用日期",
    "出差开始日期",
    "出差结束日期",
    "商户",
    "发票号码",
    "票据状态",
    "审批状态",
    "预算编码",
    "用途说明",
]

EMPLOYEES = [
    ("E1001", "销售部", "L2", "SALES-TRAVEL"),
    ("E1002", "销售部", "L3", "SALES-TRAVEL"),
    ("E2001", "交付部", "L2", "DELIVERY-TRAVEL"),
    ("E2002", "交付部", "L3", "DELIVERY-TRAVEL"),
    ("E3001", "产品部", "L2", "PROD-RND"),
    ("E3002", "产品部", "L4", "PROD-RND"),
    ("E4001", "运营部", "L1", "OPS-GENERAL"),
    ("E4002", "运营部", "L3", "OPS-GENERAL"),
]

CITIES = [
    ("北京", "一线"),
    ("上海", "一线"),
    ("广州", "一线"),
    ("成都", "二线"),
    ("杭州", "二线"),
    ("武汉", "二线"),
    ("合肥", "三线"),
    ("南昌", "三线"),
]

HOTEL_CAPS = {
    ("一线", "L1"): 500,
    ("一线", "L2"): 500,
    ("一线", "L3"): 700,
    ("一线", "L4"): 900,
    ("二线", "L1"): 400,
    ("二线", "L2"): 400,
    ("二线", "L3"): 600,
    ("二线", "L4"): 800,
    ("三线", "L1"): 350,
    ("三线", "L2"): 350,
    ("三线", "L3"): 500,
    ("三线", "L4"): 700,
}

MERCHANTS = {
    "住宿": ["云栖酒店", "城际酒店", "汇景酒店"],
    "交通": ["城市出行", "高铁票务", "机场快线"],
    "客户招待": ["聚合餐饮", "江南餐厅", "和悦会馆"],
    "办公采购": ["晨光办公", "企业采购中心", "数码供应站"],
}


def base_ticket(index: int, rng: random.Random) -> dict[str, object]:
    employee_id, department, level, budget = rng.choice(EMPLOYEES)
    city, city_tier = rng.choice(CITIES)
    expense_type = rng.choice(list(MERCHANTS))
    trip_start = dt.date(2026, 6, rng.randint(1, 24))
    trip_end = trip_start + dt.timedelta(days=rng.randint(1, 3))
    expense_date = trip_start + dt.timedelta(days=rng.randint(0, (trip_end - trip_start).days))
    merchant = rng.choice(MERCHANTS[expense_type])

    if expense_type == "住宿":
        amount = round(HOTEL_CAPS[(city_tier, level)] * rng.uniform(0.55, 0.92), 2)
        description = f"{city}客户项目出差住宿"
    elif expense_type == "交通":
        amount = round(rng.uniform(45, 280), 2)
        description = f"{city}出差交通"
    elif expense_type == "客户招待":
        amount = round(rng.uniform(300, 900), 2)
        description = f"{city}客户沟通工作餐"
    else:
        amount = round(rng.uniform(120, 1600), 2)
        description = "项目办公用品采购"

    needs_approval = expense_type == "办公采购" and amount >= 2000
    needs_approval = needs_approval or (expense_type == "客户招待" and amount >= 1000)
    return {
        "Ticket ID": f"EXP-202606-{index:04d}",
        "员工编号": employee_id,
        "部门": department,
        "岗位等级": level,
        "费用类型": expense_type,
        "金额": amount,
        "城市": city,
        "城市等级": city_tier,
        "费用日期": expense_date.isoformat(),
        "出差开始日期": trip_start.isoformat(),
        "出差结束日期": trip_end.isoformat(),
        "商户": merchant,
        "发票号码": f"INV-{2026060000 + index}",
        "票据状态": "完整",
        "审批状态": "已审批" if needs_approval else "无需额外审批",
        "预算编码": budget,
        "用途说明": description,
    }


def apply_issue(ticket: dict[str, object], issue: str, prior: list[dict[str, object]]) -> None:
    if issue == "missing_invoice":
        ticket["票据状态"] = "缺失"
        ticket["发票号码"] = ""
    elif issue == "over_limit":
        key = (str(ticket["城市等级"]), str(ticket["岗位等级"]))
        ticket["费用类型"] = "住宿"
        ticket["金额"] = HOTEL_CAPS[key] + 180
        ticket["用途说明"] = f"{ticket['城市']}客户项目出差住宿"
    elif issue == "date_mismatch":
        end = dt.date.fromisoformat(str(ticket["出差结束日期"]))
        ticket["费用日期"] = (end + dt.timedelta(days=4)).isoformat()
    elif issue == "missing_approval":
        ticket["费用类型"] = "客户招待"
        ticket["金额"] = 1680
        ticket["审批状态"] = "未提交"
        ticket["用途说明"] = "客户项目阶段性沟通工作餐"
    elif issue == "invalid_budget":
        ticket["预算编码"] = "UNKNOWN-001"
    elif issue == "duplicate_invoice":
        source = prior[0] if prior else ticket
        ticket["发票号码"] = source["发票号码"]
    elif issue == "category_mismatch":
        ticket["费用类型"] = "办公采购"
        ticket["用途说明"] = "客户项目阶段性沟通晚餐"
        ticket["商户"] = "江南餐厅"
    elif issue == "city_tier_mismatch":
        ticket["城市"] = "北京"
        ticket["城市等级"] = "三线"
    else:
        raise ValueError(f"unknown issue: {issue}")


def generate(seed: int = 20260725) -> tuple[list[dict[str, object]], list[str]]:
    rng = random.Random(seed)
    tickets: list[dict[str, object]] = []
    profiles: list[str] = []
    issues = [
        "missing_invoice",
        "over_limit",
        "date_mismatch",
        "missing_approval",
        "invalid_budget",
        "duplicate_invoice",
        "category_mismatch",
        "city_tier_mismatch",
    ]

    for index in range(1, 201):
        ticket = base_ticket(index, rng)
        if index <= 60:
            profile = "normal"
        elif index <= 160:
            profile = "single"
            apply_issue(ticket, issues[(index - 61) % len(issues)], tickets)
        elif index <= 190:
            profile = "multi"
            first = issues[(index - 161) % len(issues)]
            second = issues[(index - 158) % len(issues)]
            apply_issue(ticket, first, tickets)
            apply_issue(ticket, second, tickets)
        else:
            profile = "manual_review"
            ticket["费用类型"] = "办公采购"
            ticket["金额"] = round(rng.uniform(1800, 4500), 2)
            ticket["审批状态"] = "紧急采购事后补批"
            ticket["用途说明"] = "客户现场突发故障应急采购，制度未覆盖当前情形"
        tickets.append(ticket)
        profiles.append(profile)

    return tickets, profiles


def write_csv(path: Path, tickets: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(tickets)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "assets" / "expense_tickets.csv",
    )
    parser.add_argument("--seed", type=int, default=20260725)
    args = parser.parse_args()
    tickets, profiles = generate(args.seed)
    write_csv(args.output, tickets)
    counts = {profile: profiles.count(profile) for profile in sorted(set(profiles))}
    print(f"created {len(tickets)} tickets at {args.output}")
    print(counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
