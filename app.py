"""Streamlit interface for the JobPilot AI single-agent demo."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

import streamlit as st

from demo import EmailDemo
from jobmail_agent import JobMailAgent, OpenAICompatibleClient


PROJECT_DIR = Path(__file__).resolve().parent
REPORT_DIR = PROJECT_DIR / "output" / "reports"
QUALITY_METRICS_PATH = REPORT_DIR / "eval_quality_metrics.json"
BADCASE_PATH = REPORT_DIR / "badcase_report.csv"
MARKDOWN_REPORT_PATH = PROJECT_DIR / "docs" / "EVALUATION_REPORT.md"


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _load_badcases(path: Path):
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


st.set_page_config(
    page_title="JobPilot AI · 智能求职邮件助手",
    page_icon="✉️",
    layout="wide",
)
st.title("JobPilot AI · 智能求职邮件助手")
st.caption("单 Agent + 工具调用 + 本地 RAG + 离线降级。所有结果均需人工确认，系统不会发送邮件。")

view_mode = st.sidebar.radio("选择模式", ["单封邮件分析", "评测看板"], index=0)

if view_mode == "评测看板":
    st.subheader("LLM 应用评测看板")
    st.caption("展示扩展评测集的结构化输出、RAG 命中、回复安全性和 badcase 分布。")

    if not QUALITY_METRICS_PATH.exists() or not BADCASE_PATH.exists():
        st.warning("尚未生成评测报告。请先在终端运行：python evaluate_quality.py")
        st.stop()

    metrics = _load_json(QUALITY_METRICS_PATH)
    badcases = _load_badcases(BADCASE_PATH)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("样本数", metrics["total_evaluated"])
    col2.metric("分类准确率", metrics["classification_acc"])
    col3.metric("字段合法率", metrics["structured_output_valid_rate"])
    col4.metric("Badcase 数", metrics["badcase_count"])

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("岗位匹配率", metrics["position_match_rate"])
    col6.metric("Deadline 准确率", metrics["deadline_iso_acc"])
    col7.metric("RAG Top-1", metrics["retrieval_top1_type_accuracy"])
    col8.metric("回复安全率", metrics["reply_safety_pass_rate"])

    dist_tab, badcase_tab, report_tab = st.tabs(["分布与指标", "Badcase 表", "评测报告"])
    with dist_tab:
        st.write("**标签分布**")
        st.json(metrics["label_distribution"])
        st.write("**Badcase 类型分布**")
        st.json(metrics["badcase_type_distribution"])

    with badcase_tab:
        if badcases:
            st.dataframe(badcases, use_container_width=True, hide_index=True)
        else:
            st.success("当前评测未发现 badcase。")

    with report_tab:
        if MARKDOWN_REPORT_PATH.exists():
            st.markdown(MARKDOWN_REPORT_PATH.read_text(encoding="utf-8"))
        else:
            st.info("未找到 Markdown 评测报告。")
    st.stop()

samples = EmailDemo().demo_emails
sample_labels = ["自定义输入"] + [f"{item['id']} · {item['subject']}" for item in samples]
selected_label = st.sidebar.selectbox("选择演示邮件", sample_labels)
force_offline = st.sidebar.toggle("强制使用离线工作流", value=False)
client = OpenAICompatibleClient()
configured_text = "已配置，可运行 LLM Agent" if client.is_configured else "未配置，将使用离线工作流"
st.sidebar.info(f"模型状态：{configured_text}")

selected = None if selected_label == "自定义输入" else samples[sample_labels.index(selected_label) - 1]
subject = st.text_input("邮件主题", value=selected["subject"] if selected else "")
sender = st.text_input("发件人", value=selected["sender"] if selected else "")
date = st.text_input(
    "邮件时间",
    value=selected["date"] if selected else datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
)
body = st.text_area("邮件正文", value=selected["body"] if selected else "", height=190)

if st.button("运行 Agent", type="primary", use_container_width=True):
    try:
        with st.spinner("正在调用工具并整理结果..."):
            st.session_state["jobmail_result"] = JobMailAgent(llm_client=client).process(
                {"subject": subject, "sender": sender, "date": date, "body": body},
                force_offline=force_offline,
            )
    except Exception as exc:
        st.error(f"处理失败：{exc}")

result = st.session_state.get("jobmail_result")
if result:
    mode_name = "LLM Agent Mode" if result["mode"] == "llm_agent" else "Offline Workflow Mode"
    st.subheader(f"运行结果 · {mode_name}")
    if result["fallback"]["used"]:
        st.warning(f"已使用离线降级：{result['fallback']['reason']}")

    classification = result["classification"]
    extracted = result["extracted_info"]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("邮件类型", classification["type"])
    col2.metric("优先级", classification["priority"])
    col3.metric("岗位", extracted["position"])
    col4.metric("截止状态", extracted["deadline_status"])

    analysis_tab, reply_tab, rag_tab, trace_tab = st.tabs(
        ["结构化分析", "回复草稿", "RAG 来源", "工具轨迹"]
    )
    with analysis_tab:
        st.write(f"**公司：** {extracted['company']}")
        st.write(f"**截止时间：** {extracted['deadline_raw']} / {extracted['deadline_iso']}")
        st.write(f"**行动建议：** {result['action_suggestion']}")
        st.write("**待办事项：**")
        st.write(extracted.get("todos") or ["未识别"])
        st.warning("；".join(result["human_review"]["reasons"]))

    with reply_tab:
        reply = result.get("reply_draft")
        if reply:
            st.text_input("回复主题", value=reply["subject"], key="reply_subject")
            st.text_area("可编辑回复正文", value=reply["content"], height=220, key="reply_content")
            confirmed = st.checkbox("我已人工核对邮件事实与回复内容")
            if confirmed:
                st.success("已完成演示确认。此应用不会发送邮件。")
        else:
            st.info("该类型邮件默认不生成回复草稿。")

    with rag_tab:
        hits = result["retrieval"]["hits"]
        if not hits:
            st.info("没有检索到知识库内容。")
        for hit in hits:
            with st.expander(f"{hit['title']} · {hit['source']} · score={hit['score']}"):
                st.write(hit["content"])

    with trace_tab:
        st.dataframe(result["trace"], use_container_width=True, hide_index=True)
        with st.expander("查看完整结构化 JSON"):
            st.json(result)
