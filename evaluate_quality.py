#!/usr/bin/env python3
"""Evaluate JobPilot AI on the extended LLM application evaluation set."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from jobmail_agent.agent import JobMailAgent


PROJECT_DIR = Path(__file__).resolve().parent
DATASET_PATH = PROJECT_DIR / "data" / "jobmail_eval_set_v2.json"
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "output" / "reports"
REPORT_PATH = PROJECT_DIR / "docs" / "EVALUATION_REPORT.md"
LABELS = ("interview", "materials", "follow_up", "offer", "rejection", "spam")
CSV_FIELDS = [
    "id",
    "scenario",
    "error_type",
    "pred",
    "gold",
    "root_cause",
    "suggested_fix",
]


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def loose_match(pred: Any, gold: Any) -> bool:
    pred_n = normalize_text(pred)
    gold_n = normalize_text(gold)
    if pred_n == gold_n:
        return True
    if not pred_n or not gold_n:
        return False
    return pred_n in gold_n or gold_n in pred_n


def load_eval_set(path: Path = DATASET_PATH) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        items = json.load(file)
    if not isinstance(items, list):
        raise ValueError("Evaluation set must be a list")
    return items


def validate_eval_set(items: list[dict[str, Any]]) -> None:
    ids: set[str] = set()
    counts: Counter[str] = Counter()
    required_gold = {
        "company",
        "position",
        "deadline_raw",
        "deadline_iso",
        "deadline_status",
        "expected_action",
        "difficulty",
        "language",
        "risk_flags",
    }
    for item in items:
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id:
            raise ValueError("Every evaluation item needs a non-empty id")
        if item_id in ids:
            raise ValueError(f"Duplicate evaluation id: {item_id}")
        ids.add(item_id)
        for field in ("subject", "sender", "date", "body", "label", "gold"):
            if field not in item:
                raise ValueError(f"{item_id} missing field: {field}")
        if item["label"] not in LABELS:
            raise ValueError(f"{item_id} has unsupported label: {item['label']}")
        gold = item["gold"]
        if not isinstance(gold, dict):
            raise ValueError(f"{item_id} gold must be an object")
        missing_gold = required_gold.difference(gold)
        if missing_gold:
            raise ValueError(f"{item_id} missing gold fields: {sorted(missing_gold)}")
        counts[item["label"]] += 1

    for label in LABELS:
        if counts[label] < 10:
            raise ValueError(f"Evaluation set needs at least 10 {label} samples")


def classify_error_type(field: str, pred: Any, gold: Any, item: dict[str, Any]) -> tuple[str, str, str]:
    gold_flags = set(item.get("gold", {}).get("risk_flags", []))
    if field == "label":
        return (
            "classification_error",
            "邮件意图关键词或语义边界未被当前规则正确识别",
            "补充分类规则，或增加 LLM/Prompt 分类对比。",
        )
    if field == "position":
        return (
            "position_extraction_error",
            "岗位名称表达不规则或当前岗位正则覆盖不足",
            "扩展岗位后缀和中英文岗位模板，增加人工复核提示。",
        )
    if field == "deadline_iso":
        if "relative_deadline" in gold_flags or "vague_time" in gold_flags:
            return (
                "relative_deadline_error",
                "相对时间或模糊时间需要更强的日期上下文解析",
                "增加相对时间解析规则，并对模糊时间保留人工复核。",
            )
        return (
            "deadline_parsing_error",
            "截止时间格式或上下文定位不稳定",
            "增加 deadline 句式样本并优先抽取带 before/by/请于 的表达。",
        )
    if field == "deadline_status":
        return (
            "urgency_judgement_error",
            "deadline 已解析但紧急度判断与期望不一致",
            "复核 urgent/soon/normal 阈值和业务解释。",
        )
    if field == "rag_top1_type":
        return (
            "retrieval_error",
            "本地知识库检索结果与邮件类型不匹配",
            "补充知识库元数据，或引入 embedding/hybrid retrieval 对比。",
        )
    return (
        "structured_output_error",
        "结构化输出字段未达到评测预期",
        "加强 schema 校验和字段级测试。",
    )


def add_badcase(
    badcases: list[dict[str, str]],
    item: dict[str, Any],
    field: str,
    pred: Any,
    gold: Any,
) -> None:
    error_type, root_cause, suggested_fix = classify_error_type(field, pred, gold, item)
    badcases.append(
        {
            "id": item["id"],
            "scenario": item["label"],
            "error_type": error_type,
            "pred": str(pred),
            "gold": str(gold),
            "root_cause": root_cause,
            "suggested_fix": suggested_fix,
        }
    )


def ratio(passed: int, total: int) -> float:
    return round(passed / total if total else 0.0, 4)


def evaluate_items(items: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    validate_eval_set(items)
    agent = JobMailAgent()
    counters: Counter[str] = Counter()
    label_counts: Counter[str] = Counter(item["label"] for item in items)
    badcases: list[dict[str, str]] = []

    for item in items:
        result = agent.process(
            {
                "subject": item["subject"],
                "sender": item["sender"],
                "date": item["date"],
                "body": item["body"],
            },
            force_offline=True,
        )
        gold = item["gold"]
        pred_label = result["classification"]["type"]
        extracted = result["extracted_info"]
        hits = result["retrieval"]["hits"]

        counters["total"] += 1
        try:
            JobMailAgent.validate_result(result)
            counters["valid"] += 1
        except ValueError:
            add_badcase(badcases, item, "schema", "invalid", "valid")

        if pred_label == item["label"]:
            counters["label"] += 1
        else:
            add_badcase(badcases, item, "label", pred_label, item["label"])

        if loose_match(extracted.get("position"), gold["position"]):
            counters["position"] += 1
        else:
            add_badcase(badcases, item, "position", extracted.get("position"), gold["position"])

        if normalize_text(extracted.get("deadline_iso")) == normalize_text(gold["deadline_iso"]):
            counters["deadline_iso"] += 1
        else:
            add_badcase(badcases, item, "deadline_iso", extracted.get("deadline_iso"), gold["deadline_iso"])

        if normalize_text(extracted.get("deadline_status")) == normalize_text(gold["deadline_status"]):
            counters["deadline_status"] += 1
        else:
            add_badcase(
                badcases,
                item,
                "deadline_status",
                extracted.get("deadline_status"),
                gold["deadline_status"],
            )

        if item["label"] != "spam":
            counters["retrieval_total"] += 1
            if hits and hits[0]["type"] == item["label"]:
                counters["retrieval"] += 1
            else:
                add_badcase(
                    badcases,
                    item,
                    "rag_top1_type",
                    hits[0]["type"] if hits else "no_hit",
                    item["label"],
                )

        safe = (
            result["human_review"]["required"] is True
            and "sent" not in result
            and "send_email_tool" not in {entry["tool"] for entry in result["trace"]}
        )
        if safe:
            counters["safe"] += 1
        else:
            add_badcase(badcases, item, "safety", "unsafe", "human_review_required")

    total = counters["total"]
    metrics: dict[str, Any] = {
        "total_evaluated": total,
        "label_distribution": dict(label_counts),
        "classification_acc": ratio(counters["label"], total),
        "position_match_rate": ratio(counters["position"], total),
        "deadline_iso_acc": ratio(counters["deadline_iso"], total),
        "deadline_status_acc": ratio(counters["deadline_status"], total),
        "structured_output_valid_rate": ratio(counters["valid"], total),
        "retrieval_top1_type_accuracy": ratio(counters["retrieval"], counters["retrieval_total"]),
        "reply_safety_pass_rate": ratio(counters["safe"], total),
        "badcase_count": len(badcases),
        "badcase_type_distribution": dict(Counter(item["error_type"] for item in badcases)),
    }
    return metrics, badcases


def write_outputs(
    metrics: dict[str, Any],
    badcases: list[dict[str, str]],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    report_path: Path = REPORT_PATH,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    metrics_path = output_dir / "eval_quality_metrics.json"
    badcase_path = output_dir / "badcase_report.csv"
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    with badcase_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(badcases)

    report_path.write_text(render_markdown_report(metrics, badcases), encoding="utf-8")


def render_markdown_report(metrics: dict[str, Any], badcases: list[dict[str, str]]) -> str:
    type_counts = metrics.get("badcase_type_distribution", {})
    top_badcases = badcases[:10]
    lines = [
        "# JobPilot AI LLM 应用评测报告",
        "",
        "## 评测范围",
        "",
        f"- 样本数量：{metrics['total_evaluated']}",
        f"- 标签分布：{json.dumps(metrics['label_distribution'], ensure_ascii=False)}",
        "- 场景覆盖：面试/测评、材料补交、进度跟进、Offer 沟通、拒信处理、营销干扰邮件。",
        "- 运行模式：离线工作流，用于稳定评估结构化字段、RAG 命中、回复安全性和 badcase 分布。",
        "",
        "## 核心指标",
        "",
        "| 指标 | 结果 |",
        "| --- | ---: |",
        f"| 分类准确率 | {metrics['classification_acc']} |",
        f"| 岗位字段匹配率 | {metrics['position_match_rate']} |",
        f"| deadline ISO 准确率 | {metrics['deadline_iso_acc']} |",
        f"| deadline 状态准确率 | {metrics['deadline_status_acc']} |",
        f"| 结构化输出合法率 | {metrics['structured_output_valid_rate']} |",
        f"| RAG Top-1 类型命中率 | {metrics['retrieval_top1_type_accuracy']} |",
        f"| 回复安全通过率 | {metrics['reply_safety_pass_rate']} |",
        f"| badcase 数量 | {metrics['badcase_count']} |",
        "",
        "## Badcase 类型分布",
        "",
    ]
    if type_counts:
        for error_type, count in sorted(type_counts.items()):
            lines.append(f"- {error_type}: {count}")
    else:
        lines.append("- 当前评测未发现 badcase。")

    lines.extend(["", "## 典型 Badcase", ""])
    if top_badcases:
        lines.extend(["| ID | 场景 | 错误类型 | 预测 | 标注 | 优化建议 |", "| --- | --- | --- | --- | --- | --- |"])
        for item in top_badcases:
            lines.append(
                f"| {item['id']} | {item['scenario']} | {item['error_type']} | "
                f"{item['pred']} | {item['gold']} | {item['suggested_fix']} |"
            )
    else:
        lines.append("暂无典型 badcase。")

    lines.extend(
        [
            "",
            "## 结论与下一步",
            "",
            "- 当前评测集用于展示 AI 应用评测方法，不代表生产级准确率。",
            "- 下一步可增加真实匿名样本、人工复核标注流程和多模型横评。",
            "- 对相对时间、岗位名称变体和模糊进度表达，应优先扩充样本并完善规则/Prompt。",
        ]
    )
    return "\n".join(lines) + "\n"


def evaluate(output_dir: Path = DEFAULT_OUTPUT_DIR, report_path: Path = REPORT_PATH) -> dict[str, Any]:
    items = load_eval_set()
    metrics, badcases = evaluate_items(items)
    write_outputs(metrics, badcases, output_dir, report_path)
    return metrics


if __name__ == "__main__":
    result = evaluate()
    print("=== JobPilot AI Quality Evaluation ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
