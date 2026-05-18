# JobMail AI - Recruitment Email Assistant

JobMail AI is an AI-assisted recruitment email workflow prototype for students and early-career candidates. It helps users classify recruitment emails, extract key information, structure deadlines, generate action suggestions, and draft editable replies.

The project is designed as a lightweight, explainable MVP for AI product / applied AI / data analytics internship applications.

## Problem

Students often apply to multiple internships or graduate roles at the same time. Recruitment emails can include interview invitations, online assessments, material requests, offer discussions, rejections, follow-up updates, and spam-like promotional messages.

Manually checking every email is time-consuming and risky because important deadlines, interview times, and required actions can be missed.

## Core Workflow

```text
Recruitment email
-> classify_email()
-> extract_info()
-> infer_position() / normalize_position_label()
-> infer_deadline() / build_deadline_meta()
-> infer_action_suggestion()
-> generate_reply()
-> Human confirmation
```

## Features

- Classifies emails into `interview`, `materials`, `follow_up`, `offer`, `rejection`, and `spam`
- Extracts dates, times, phone numbers, email addresses, todos, company, position, and deadline information
- Normalizes job positions such as `AI Product Intern`, `AIGC Product Intern`, and `Product Strategy Intern`
- Structures deadlines into `deadline_raw`, `deadline_iso`, `deadline_status`, and `deadline_hours_left`
- Generates action suggestions based on email category and deadline urgency
- Generates editable reply drafts for interview, material request, offer, and general scenarios
- Provides an evaluation script with strict and loose metrics

## Project Structure

```text
jobmail-ai/
├── README.md
├── demo.py
├── evaluate.py
├── requirements.txt
├── PRD_LITE.md
├── PROJECT_DESCRIPTION.md
├── data/
│   ├── jobmail_samples.json
│   └── jobmail_eval_gold.json
└── docs/
    ├── FIELD_DESIGN.md
    └── PRODUCT_ACTION_MAP.md
```

## Quick Start

This demo version uses only the Python standard library. Python 3.8+ is recommended.

Run the demo:

```bash
python3 demo.py
```

Run the evaluation:

```bash
python3 evaluate.py
```

## Evaluation

The evaluation script compares predicted outputs against the labeled demo set in `data/jobmail_eval_gold.json`.

Current V1 demo-set results:

```text
total_evaluated: 12
classification_acc_strict: 1.0
position_acc_strict: 1.0
position_acc_loose: 1.0
deadline_acc_strict: 1.0
deadline_acc_loose: 1.0
full_match_acc_strict: 1.0
full_match_acc_loose: 1.0
mismatch_count: 0
```

Note: the current evaluation set is small and designed for MVP validation. The next step is to expand the dataset with more anonymized real-world samples.

## Product Boundary

This project is positioned as:

```text
AI suggestion + human confirmation
```

It does not automatically send emails. Recruitment communication is a high-risk scenario, so all generated replies and action suggestions should be reviewed by the user before execution.

## Key Documents

- `PRD_LITE.md`: lightweight product requirement document
- `PROJECT_DESCRIPTION.md`: project background and product explanation
- `docs/FIELD_DESIGN.md`: structured field design
- `docs/PRODUCT_ACTION_MAP.md`: action suggestion mapping logic

## Future Improvements

- Expand evaluation data to 50+ anonymized samples
- Add an optional LLM extraction mode and compare it with the rule-based baseline
- Build a lightweight Streamlit demo page for interviews and portfolio presentation
