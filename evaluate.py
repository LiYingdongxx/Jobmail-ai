#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evaluate JobMail AI quality on labeled demo samples."""

import json
import re
from pathlib import Path

from demo import EmailDemo


def normalize_text(text):
    return re.sub(r"\s+", " ", str(text)).strip().lower()


def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def calc_acc(correct, total):
    return round((correct / total if total else 0.0), 4)


def loose_text_match(pred, gold):
    pred_n = normalize_text(pred)
    gold_n = normalize_text(gold)
    if pred_n == gold_n:
        return True
    if not pred_n or not gold_n:
        return False
    return pred_n in gold_n or gold_n in pred_n


def evaluate():
    project_dir = Path(__file__).resolve().parent
    gold_path = project_dir / "data" / "jobmail_eval_gold.json"
    output_dir = project_dir / "output" / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    gold_items = load_json(gold_path)
    gold_by_id = {item["id"]: item for item in gold_items}

    demo = EmailDemo()

    total = 0
    cls_correct_strict = 0
    pos_correct_strict = 0
    pos_correct_loose = 0
    ddl_correct_strict = 0
    ddl_correct_loose = 0
    full_match_strict = 0
    full_match_loose = 0
    mismatches = []

    for email in demo.demo_emails:
        email_id = email.get("id")
        gold = gold_by_id.get(email_id)
        if not gold:
            continue

        total += 1
        classification = demo.classify_email(email)
        extracted = demo.extract_info(email, classification)

        pred_label = classification["type"]
        pred_position = extracted["position"]
        pred_deadline = extracted["deadline_raw"]
        pred_deadline_iso = extracted["deadline_iso"]

        gold_label = gold["label"]
        gold_position = gold["position"]
        gold_deadline = gold["deadline"]
        gold_deadline_iso = gold.get("deadline_iso", "未识别")

        cls_ok_strict = normalize_text(pred_label) == normalize_text(gold_label)
        pos_ok_strict = normalize_text(pred_position) == normalize_text(gold_position)
        pos_ok_loose = loose_text_match(pred_position, gold_position)
        ddl_ok_strict = normalize_text(pred_deadline) == normalize_text(gold_deadline)

        if normalize_text(gold_deadline_iso) != "未识别":
            ddl_ok_loose = normalize_text(pred_deadline_iso) == normalize_text(gold_deadline_iso)
        else:
            ddl_ok_loose = loose_text_match(pred_deadline, gold_deadline)

        cls_correct_strict += int(cls_ok_strict)
        pos_correct_strict += int(pos_ok_strict)
        pos_correct_loose += int(pos_ok_loose)
        ddl_correct_strict += int(ddl_ok_strict)
        ddl_correct_loose += int(ddl_ok_loose)

        if cls_ok_strict and pos_ok_strict and ddl_ok_strict:
            full_match_strict += 1
        if cls_ok_strict and pos_ok_loose and ddl_ok_loose:
            full_match_loose += 1

        if not (cls_ok_strict and pos_ok_strict and ddl_ok_strict):
            mismatches.append(
                {
                    "id": email_id,
                    "subject": email["subject"],
                    "pred": {
                        "label": pred_label,
                        "position": pred_position,
                        "deadline_raw": pred_deadline,
                        "deadline_iso": pred_deadline_iso,
                    },
                    "gold": {
                        "label": gold_label,
                        "position": gold_position,
                        "deadline_raw": gold_deadline,
                        "deadline_iso": gold_deadline_iso,
                    },
                    "strict_pass": {
                        "label": cls_ok_strict,
                        "position": pos_ok_strict,
                        "deadline": ddl_ok_strict,
                    },
                    "loose_pass": {
                        "position": pos_ok_loose,
                        "deadline": ddl_ok_loose,
                    },
                }
            )

    metrics = {
        "total_evaluated": total,
        "classification_acc_strict": calc_acc(cls_correct_strict, total),
        "position_acc_strict": calc_acc(pos_correct_strict, total),
        "position_acc_loose": calc_acc(pos_correct_loose, total),
        "deadline_acc_strict": calc_acc(ddl_correct_strict, total),
        "deadline_acc_loose": calc_acc(ddl_correct_loose, total),
        "full_match_acc_strict": calc_acc(full_match_strict, total),
        "full_match_acc_loose": calc_acc(full_match_loose, total),
        "mismatch_count": len(mismatches),
    }

    metrics_path = output_dir / "evaluation_metrics.json"
    mismatches_path = output_dir / "evaluation_mismatches.json"
    with metrics_path.open("w", encoding="utf-8") as file:
        json.dump(metrics, file, ensure_ascii=False, indent=2)
    with mismatches_path.open("w", encoding="utf-8") as file:
        json.dump(mismatches, file, ensure_ascii=False, indent=2)

    print("=== JobMail AI Evaluation (V1) ===")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(f"\nMetrics saved to: {metrics_path}")
    print(f"Mismatches saved to: {mismatches_path}")

    if mismatches:
        print("\n=== Strict mismatches ===")
        for item in mismatches:
            print(f"- {item['id']} | {item['subject']}")
            print(f"  label:        pred={item['pred']['label']} | gold={item['gold']['label']}")
            print(f"  position:     pred={item['pred']['position']} | gold={item['gold']['position']}")
            print(f"  deadline_raw: pred={item['pred']['deadline_raw']} | gold={item['gold']['deadline_raw']}")
            print(f"  deadline_iso: pred={item['pred']['deadline_iso']} | gold={item['gold']['deadline_iso']}")
    else:
        print("\nNo strict mismatches. All fields match gold.")


if __name__ == "__main__":
    evaluate()
