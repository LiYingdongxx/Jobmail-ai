#!/usr/bin/env python3
"""Evaluate deterministic V2 agent routing, retrieval and safety behavior."""

from __future__ import annotations

import json

from demo import EmailDemo
from jobmail_agent.agent import JobMailAgent
from jobmail_agent.llm import LLMClientError


class FailingClient:
    is_configured = True

    def chat(self, messages, tools):
        raise LLMClientError("evaluation failure")


def ratio(passed: int, total: int) -> float:
    return round(passed / total if total else 0.0, 4)


def evaluate() -> dict[str, float | int]:
    samples = EmailDemo().demo_emails
    agent = JobMailAgent()
    completed = 0
    valid = 0
    route_correct = 0
    retrieval_correct = 0
    retrieval_total = 0
    safe = 0

    for email in samples:
        result = agent.process(email, force_offline=True)
        completed += int(bool(result.get("action_suggestion")))
        try:
            JobMailAgent.validate_result(result)
            valid += 1
        except ValueError:
            pass

        tool_names = [entry["tool"] for entry in result["trace"]]
        required = {
            "classify_email_tool",
            "extract_info_tool",
            "deadline_parser_tool",
            "action_suggestion_tool",
        }
        route_correct += int(required.issubset(tool_names))

        if email["label"] != "spam":
            retrieval_total += 1
            hits = result["retrieval"]["hits"]
            retrieval_correct += int(bool(hits) and hits[0]["type"] == email["label"])

        no_send_tool = "send_email_tool" not in tool_names
        human_review = result["human_review"]["required"] is True
        safe += int(no_send_tool and human_review and "sent" not in result)

    fallback_result = JobMailAgent(llm_client=FailingClient()).process(samples[0])
    fallback_success = int(
        fallback_result["mode"] == "offline_workflow"
        and fallback_result["classification"]["type"] == samples[0]["label"]
    )

    total = len(samples)
    return {
        "total_evaluated": total,
        "task_completion_rate": ratio(completed, total),
        "structured_output_valid_rate": ratio(valid, total),
        "tool_route_pass_rate": ratio(route_correct, total),
        "retrieval_top1_type_accuracy": ratio(retrieval_correct, retrieval_total),
        "reply_safety_pass_rate": ratio(safe, total),
        "llm_failure_fallback_success": fallback_success,
    }


if __name__ == "__main__":
    print("=== JobMail AI Evaluation (V2 Offline + Fallback) ===")
    print(json.dumps(evaluate(), ensure_ascii=False, indent=2))
