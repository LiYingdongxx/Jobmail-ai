#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
求职邮件助手 - 演示版本
JobMail AI - Demo Version

无需配置真实邮箱，直接体验求职场景下的邮件分类、信息提取和回复建议。
"""

import json
import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path


class EmailDemo:
    def __init__(self):
        self.project_dir = Path(__file__).resolve().parent
        self.demo_emails = self.load_demo_emails()
        self.en_month_map = {
            "jan": 1, "january": 1,
            "feb": 2, "february": 2,
            "mar": 3, "march": 3,
            "apr": 4, "april": 4,
            "may": 5,
            "jun": 6, "june": 6,
            "jul": 7, "july": 7,
            "aug": 8, "august": 8,
            "sep": 9, "sept": 9, "september": 9,
            "oct": 10, "october": 10,
            "nov": 11, "november": 11,
            "dec": 12, "december": 12,
        }
        
        self.classification_rules = {
            'interview_keywords': ['面试', 'interview', '一面', '二面', '笔试', '测评', 'assessment', 'coding task'],
            'materials_keywords': [
                '材料', '作品集', '成绩单', '证明', '补交', '补充', '附件', '项目说明',
                'portfolio', 'document', 'submit', 'upload', 'attachment', 'github', 'missing'
            ],
            'follow_up_keywords': [
                '进度', '跟进', '等待', '复核', '评估中', '核验', 'status', 'update',
                'follow up', 'under review', 'no further action', 'talent pool', 'decision'
            ],
            'offer_keywords': ['offer', '录用', '拟录用', '录用意向', '入职', 'onboard', '到岗', 'pre-offer'],
            'rejection_keywords': [
                '未进入', '感谢关注', '未通过', '暂未通过', '不进入后续', '暂不安排',
                'regret', 'not move forward', 'not to proceed', 'cannot offer', 'not proceed'
            ],
            'spam_keywords': [
                '广告', '推广', '营销', '优惠', '立减', '课程', '资料包', '保过班', '模板',
                '内推名额', '会员', '特价', 'promotion', 'discount', 'course', 'template',
                'bootcamp', 'buy today', 'limited time', 'coaching'
            ]
        }
        
        self.reply_templates = {
            'interview': {
                'zh': '您好，感谢您的面试邀请。我已收到关于“{subject}”的安排，并确认会准时参加。如需我提前准备额外材料，请随时告知。\n\n此致\n敬礼',
                'en': 'Hello, thank you for the interview invitation. I have received the arrangement for "{subject}" and confirm that I will attend on time. Please let me know if any additional materials are needed.\n\nBest regards'
            },
            'materials': {
                'zh': '您好，感谢您的邮件。我已收到关于“{subject}”的材料补充请求，会在要求时间前整理并发送相关文件。如需特定格式，请告诉我。\n\n此致\n敬礼',
                'en': 'Hello, thank you for your email. I have received the material request regarding "{subject}" and will send the requested documents before the deadline. Please let me know if a specific format is required.\n\nBest regards'
            },
            'offer': {
                'zh': '您好，非常感谢贵司的录用沟通。我已收到“{subject}”相关信息，并会尽快确认到岗时间及联系方式。期待加入团队。\n\n此致\n敬礼',
                'en': 'Hello, thank you very much for the offer update. I have received the information regarding "{subject}" and will confirm my onboarding date and contact number shortly. I look forward to joining the team.\n\nBest regards'
            },
            'general': {
                'zh': '您好，已收到您的邮件。我会尽快查看相关内容，并在需要时及时回复。感谢您的通知。',
                'en': 'Hello, I have received your email and will review the details shortly. Thank you for the update.'
            }
        }

    def load_demo_emails(self):
        """从项目数据文件中读取演示样本。"""
        sample_path = self.project_dir / "data" / "jobmail_samples.json"
        with sample_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def infer_company(self, email):
        """根据发件人域名推断公司名。"""
        sender = email["sender"].split("@")[-1]
        company = sender.split(".")[0]
        company = company.replace("-", " ")
        return company.title()

    def normalize_whitespace(self, text):
        """压缩多余空白，便于规则匹配与输出。"""
        return re.sub(r"\s+", " ", text).strip()

    def extract_datetime_candidates(self, text):
        """提取常见中英文日期时间表达。"""
        date_pattern = (
            r"(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}"
            r"|\d{1,2}\s*月\s*\d{1,2}\s*日"
            r"|\d{1,2}/\d{1,2}(?:/\d{2,4})?"
            r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|June|July)\s+\d{1,2}(?:,\s*\d{4})?)"
        )
        time_pattern = (
            r"(?:\d{1,2}:\d{2}(?:\s*(?:AM|PM))?"
            r"|\d{1,2}(?::\d{2})?\s*(?:AM|PM)"
            r"|(?:上午|下午|中午|晚上)?\s*\d{1,2}\s*点(?:\d{1,2}分)?)"
        )

        patterns = [
            rf"{date_pattern}\s*(?:,|，|at|@|上午|下午|中午|晚上)?\s*{time_pattern}",
            date_pattern,
            time_pattern
        ]

        candidates = []
        for pattern in patterns:
            candidates.extend(re.findall(pattern, text, flags=re.IGNORECASE))

        deduped = []
        seen = set()
        for candidate in candidates:
            clean_candidate = self.normalize_whitespace(candidate)
            key = clean_candidate.lower()
            if clean_candidate and key not in seen:
                deduped.append(clean_candidate)
                seen.add(key)
        return deduped

    def dedupe_text_list(self, items):
        """按文本值去重，保留原始顺序。"""
        deduped = []
        seen = set()
        for item in items:
            clean_item = self.normalize_whitespace(item)
            key = clean_item.lower()
            if clean_item and key not in seen:
                deduped.append(clean_item)
                seen.add(key)
        return deduped

    def normalize_position_label(self, position):
        """将岗位名归一化，便于统计与展示。"""
        if not position or position == "未知岗位":
            return "未知岗位"

        normalized = self.normalize_whitespace(position)
        mapping_rules = [
            (r"(?:ai|aigc)\s*产品\s*实习(?:生)?|ai product intern(?:ship)?", "AI Product Intern"),
            (r"aigc product intern(?:ship)?", "AIGC Product Intern"),
            (r"product strategy intern(?:ship)?", "Product Strategy Intern"),
            (r"ai operations intern(?:ship)?", "AI Operations Intern"),
            (r"ai\s*产品\s*培训生", "AI Product Trainee"),
        ]

        lowered = normalized.lower()
        for pattern, target in mapping_rules:
            if re.search(pattern, lowered, flags=re.IGNORECASE):
                return target
        return normalized

    def infer_position(self, email, email_type=None):
        """从主题+正文提取岗位名称，优先返回更像“职位名”的候选。"""
        if email_type == "spam":
            return "未知岗位"

        role_suffix_pattern = r"(?:实习|实习生|培训生|工程师|经理|专员|顾问|Internship|Intern|Engineer|Manager|Specialist|Analyst)$"
        core_role_keyword_pattern = r"(?:AI|AIGC|LLM|大模型|人工智能|产品|运营|数据|测试|评测|助理|Product|Operations|Data|ML)"
        noise_pattern = r"(?:面试题|课程|优惠|模板|保过班|promotion|discount|course|template)"
        non_role_prefix_pattern = r"^(?:online assessment|application update|portfolio request|next step|offer沟通|补充材料通知|re)\s*(?:for|:|：)\s*"
        non_role_token_pattern = r"(?:assessment|request|update|next step|offer confirmation|领取|点击|感谢你关注我司|沟通阶段)"
        position_patterns = [
            r"(?:岗位|职位|role|position)\s*[:：]?\s*([A-Za-z\u4e00-\u9fa50-9/&+\-\s]{2,40}(?:Internship|Intern|实习|实习生|培训生|工程师|经理|专员))",
            r"((?:(?:AI|AIGC|大模型|人工智能)\s*)?(?:(?:产品|运营|算法|数据|研发|应用|测试|评测|助理)\s*)?(?:经理|实习|实习生|培训生|工程师|专员))",
            r"((?:AI|AIGC|LLM|ML|Prompt|Evaluation|Application|Testing|Backend|Product|Operations|Data)(?:\s+[A-Za-z]+){0,3}\s+(?:Internship|Intern|Engineer|Manager|Specialist|Analyst))",
            r"((?:[A-Za-z]+(?:\s+[A-Za-z]+){0,2}\s+)?(?:Product|Operations|Data|AI|AIGC|ML|LLM|Strategy|Prompt|Evaluation|Application|Testing|Backend)(?:\s+[A-Za-z]+){0,2}\s+(?:Internship|Intern|Engineer|Manager|Specialist|Analyst))"
        ]

        candidates = []
        for source_index, text in enumerate([email["subject"], email["body"]]):
            for pattern in position_patterns:
                for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                    raw = match.group(1) if match.lastindex else match.group(0)
                    clean_candidate = self.normalize_whitespace(
                        raw.strip("【】[]()（）:：,，。.\"' ")
                    )
                    clean_candidate = re.sub(
                        non_role_prefix_pattern,
                        "",
                        clean_candidate,
                        flags=re.IGNORECASE
                    )
                    clean_candidate = re.sub(r"^(?:for|the|your)\s+", "", clean_candidate, flags=re.IGNORECASE)
                    clean_candidate = re.sub(
                        r"(?:\s*(?:role|position|岗位|职位))$",
                        "",
                        clean_candidate,
                        flags=re.IGNORECASE
                    ).strip()
                    clean_candidate = re.sub(
                        r"\s+(?:at this time|for now)$",
                        "",
                        clean_candidate,
                        flags=re.IGNORECASE
                    ).strip()

                    if len(clean_candidate) < 3:
                        continue
                    if re.search(noise_pattern, clean_candidate, flags=re.IGNORECASE):
                        continue
                    if re.search(non_role_token_pattern, clean_candidate, flags=re.IGNORECASE):
                        continue
                    if not re.search(role_suffix_pattern, clean_candidate, flags=re.IGNORECASE):
                        continue

                    score = 0
                    if source_index == 0:
                        score += 2  # 主题优先
                    if re.search(role_suffix_pattern, clean_candidate, flags=re.IGNORECASE):
                        score += 2
                    if re.search(core_role_keyword_pattern, clean_candidate, flags=re.IGNORECASE):
                        score += 2

                    candidates.append((score, clean_candidate))

        if candidates:
            return max(candidates, key=lambda item: (item[0], -len(item[1])))[1]
        return "未知岗位"

    def infer_deadline(self, body, dates, times):
        """优先抓取“请于…前 / before ... / by ...”这类明确截止表达。"""
        normalized_body = self.normalize_whitespace(body)
        date_pattern = (
            r"(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}"
            r"|\d{1,2}\s*月\s*\d{1,2}\s*日"
            r"|\d{1,2}/\d{1,2}(?:/\d{2,4})?"
            r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|June|July)\s+\d{1,2}(?:,\s*\d{4})?)"
        )
        time_pattern = (
            r"(?:\d{1,2}:\d{2}(?:\s*(?:AM|PM))?"
            r"|\d{1,2}(?::\d{2})?\s*(?:AM|PM)"
            r"|(?:上午|下午|中午|晚上)?\s*\d{1,2}\s*点(?:\d{1,2}分)?)"
        )
        date_time_pattern = rf"{date_pattern}(?:\s*(?:,|，|at|@|上午|下午|中午|晚上)?\s*{time_pattern})?"

        explicit_deadline_patterns = [
            rf"(?:请于|请在|于|在|务必在|需在)\s*({date_time_pattern})\s*(?:前|之前)",
            rf"(?:before|by|no later than)\s+({date_time_pattern})",
            rf"(?:deadline(?:\s+is)?|due(?:\s+date)?(?:\s+is)?)\s*[:：]?\s*({date_time_pattern})"
        ]
        for pattern in explicit_deadline_patterns:
            match = re.search(pattern, normalized_body, flags=re.IGNORECASE)
            if match:
                return self.normalize_whitespace(match.group(1))

        deadline_keywords = ["截止", "截至", "before", "by", "deadline", "due", "前", "之前"]
        sentences = re.split(r"[。.!?；;\n]", body)
        for sentence in sentences:
            normalized_sentence = self.normalize_whitespace(sentence)
            if not normalized_sentence:
                continue
            lowered_sentence = normalized_sentence.lower()
            if any(keyword in normalized_sentence for keyword in deadline_keywords) or any(
                keyword in lowered_sentence for keyword in ["before", "by", "deadline", "due"]
            ):
                datetime_candidates = self.extract_datetime_candidates(normalized_sentence)
                if datetime_candidates:
                    best_candidate = next(
                        (
                            candidate for candidate in datetime_candidates
                            if re.search(date_pattern, candidate, flags=re.IGNORECASE)
                            and re.search(time_pattern, candidate, flags=re.IGNORECASE)
                        ),
                        datetime_candidates[0]
                    )
                    return best_candidate

        relative_match = re.search(
            r"(within\s+\w+\s+business\s+days|下周[一二三四五六日天]|本周[一二三四五六日天])",
            normalized_body,
            flags=re.IGNORECASE
        )
        if relative_match:
            return self.normalize_whitespace(relative_match.group(1))

        has_deadline_semantics = any(keyword in normalized_body for keyword in deadline_keywords) or any(
            keyword in normalized_body.lower() for keyword in ["before", "by", "deadline", "due"]
        )
        if has_deadline_semantics and (dates or times):
            return " ".join(dates[:1] + times[:1]).strip()
        return "未识别"

    def parse_reference_time(self, email):
        """优先用邮件时间作为截止时间推断基准。"""
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(str(email.get("date", "")), fmt)
            except ValueError:
                continue
        return datetime.now()

    def apply_day_period(self, hour, minute, period):
        """处理上午/下午/中午/晚上这类时段词。"""
        period = (period or "").strip()
        if period in ["下午", "晚上"] and hour < 12:
            hour += 12
        if period == "中午":
            if hour == 0:
                hour = 12
            elif 1 <= hour <= 11:
                hour += 12
        if period == "上午" and hour == 12:
            hour = 0
        return hour, minute

    def parse_relative_day(self, deadline_raw, base_time):
        """解析“下周二/本周三”以及“within five business days”等相对时间。"""
        text = self.normalize_whitespace(deadline_raw).lower()
        week_map = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}

        cn_match = re.search(r"(本周|下周)([一二三四五六日天])", text)
        if cn_match:
            week_tag = cn_match.group(1)
            target_weekday = week_map[cn_match.group(2)]
            current_weekday = base_time.weekday()
            if week_tag == "本周":
                delta_days = target_weekday - current_weekday
                if delta_days < 0:
                    delta_days += 7
            else:
                delta_days = (7 - current_weekday) + target_weekday
            target = base_time + timedelta(days=delta_days)
            return target.replace(hour=18, minute=0, second=0, microsecond=0), True

        en_match = re.search(r"within\s+([a-z0-9]+)\s+business\s+days", text, flags=re.IGNORECASE)
        if en_match:
            number_token = en_match.group(1).lower()
            number_map = {
                "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            }
            business_days = int(number_token) if number_token.isdigit() else number_map.get(number_token)
            if business_days:
                current = base_time
                added = 0
                while added < business_days:
                    current += timedelta(days=1)
                    if current.weekday() < 5:
                        added += 1
                return current.replace(hour=18, minute=0, second=0, microsecond=0), True
        return None, False

    def parse_absolute_deadline(self, deadline_raw, base_time):
        """解析具体日期时间文本并转为 datetime。"""
        text = self.normalize_whitespace(deadline_raw)

        ymd_match = re.search(
            r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})(?:\s+(\d{1,2}):(\d{2})(?:\s*(AM|PM))?)?",
            text,
            flags=re.IGNORECASE,
        )
        if ymd_match:
            year, month, day = [int(ymd_match.group(i)) for i in [1, 2, 3]]
            hour = int(ymd_match.group(4)) if ymd_match.group(4) else 23
            minute = int(ymd_match.group(5)) if ymd_match.group(5) else 59
            ampm = ymd_match.group(6)
            if ampm:
                if ampm.upper() == "PM" and hour < 12:
                    hour += 12
                if ampm.upper() == "AM" and hour == 12:
                    hour = 0
            return datetime(year, month, day, hour, minute), False

        cn_match = re.search(
            r"(\d{1,2})\s*月\s*(\d{1,2})\s*日(?:\s*(上午|下午|中午|晚上))?(?:\s*(\d{1,2})(?::(\d{2}))?\s*点?(?:\s*(\d{1,2})分?)?)?",
            text,
        )
        if cn_match:
            month = int(cn_match.group(1))
            day = int(cn_match.group(2))
            period = cn_match.group(3)
            hour = int(cn_match.group(4)) if cn_match.group(4) else None
            if cn_match.group(6):
                minute = int(cn_match.group(6))
            elif cn_match.group(5):
                minute = int(cn_match.group(5))
            else:
                minute = 0
            if hour is None:
                colon_time = re.search(r"(\d{1,2}):(\d{2})", text)
                if colon_time:
                    hour = int(colon_time.group(1))
                    minute = int(colon_time.group(2))
            if hour is None:
                hour = 23
                minute = 59
            hour, minute = self.apply_day_period(hour, minute, period)
            return datetime(base_time.year, month, day, hour, minute), False

        en_match = re.search(
            r"(Jan|January|Feb|February|Mar|March|Apr|April|May|Jun|June|Jul|July|Aug|August|Sep|Sept|September|Oct|October|Nov|November|Dec|December)\s+(\d{1,2})(?:,\s*(\d{4}))?(?:\s*(?:at|,)?\s*(\d{1,2})(?::(\d{2}))?\s*(AM|PM))?",
            text,
            flags=re.IGNORECASE,
        )
        if en_match:
            month_token = en_match.group(1).lower()
            month = self.en_month_map[month_token]
            day = int(en_match.group(2))
            year = int(en_match.group(3)) if en_match.group(3) else base_time.year
            hour = int(en_match.group(4)) if en_match.group(4) else 23
            minute = int(en_match.group(5)) if en_match.group(5) else (59 if en_match.group(4) is None else 0)
            ampm = en_match.group(6)
            if ampm:
                if ampm.upper() == "PM" and hour < 12:
                    hour += 12
                if ampm.upper() == "AM" and hour == 12:
                    hour = 0
            return datetime(year, month, day, hour, minute), False

        slash_match = re.search(
            r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?(?:\s+(\d{1,2}):(\d{2})(?:\s*(AM|PM))?)?",
            text,
            flags=re.IGNORECASE,
        )
        if slash_match:
            month = int(slash_match.group(1))
            day = int(slash_match.group(2))
            year = slash_match.group(3)
            if year:
                year = int(year)
                if year < 100:
                    year += 2000
            else:
                year = base_time.year
            hour = int(slash_match.group(4)) if slash_match.group(4) else 23
            minute = int(slash_match.group(5)) if slash_match.group(5) else 59
            ampm = slash_match.group(6)
            if ampm:
                if ampm.upper() == "PM" and hour < 12:
                    hour += 12
                if ampm.upper() == "AM" and hour == 12:
                    hour = 0
            return datetime(year, month, day, hour, minute), False
        return None, False

    def build_deadline_meta(self, email, deadline_raw):
        """输出结构化截止信息，支持时间紧急度判断。"""
        if not deadline_raw or deadline_raw == "未识别":
            return {
                "deadline_raw": "未识别",
                "deadline_iso": "未识别",
                "deadline_is_relative": False,
                "deadline_hours_left": None,
                "deadline_status": "unknown",
            }

        base_time = self.parse_reference_time(email)
        parsed_deadline, is_relative = self.parse_absolute_deadline(deadline_raw, base_time)
        if parsed_deadline is None:
            parsed_deadline, is_relative = self.parse_relative_day(deadline_raw, base_time)

        if parsed_deadline is None:
            return {
                "deadline_raw": deadline_raw,
                "deadline_iso": "未识别",
                "deadline_is_relative": False,
                "deadline_hours_left": None,
                "deadline_status": "unknown",
            }

        hours_left = round((parsed_deadline - base_time).total_seconds() / 3600, 1)
        if hours_left < 0:
            status = "overdue"
        elif hours_left <= 24:
            status = "urgent"
        elif hours_left <= 72:
            status = "soon"
        else:
            status = "normal"

        return {
            "deadline_raw": deadline_raw,
            "deadline_iso": parsed_deadline.strftime("%Y-%m-%d %H:%M"),
            "deadline_is_relative": is_relative,
            "deadline_hours_left": hours_left,
            "deadline_status": status,
        }

    def infer_interview_mode(self, body):
        """根据正文关键词判断面试形式。"""
        lowered_body = body.lower()
        if any(keyword in lowered_body for keyword in ["视频面试", "video interview", "video"]):
            return "video"
        if any(keyword in lowered_body for keyword in ["电话面试", "phone interview", "phone"]):
            return "phone"
        if any(keyword in lowered_body for keyword in ["线下面试", "onsite", "现场面试"]):
            return "onsite"
        return "unknown"

    def infer_action_suggestion(self, classification, extracted_info):
        """根据分类 + 截止紧急度给出下一步动作建议。"""
        email_type = classification["type"]
        deadline_status = extracted_info.get("deadline_status", "unknown")
        deadline_hours = extracted_info.get("deadline_hours_left")
        interview_mode = extracted_info.get("interview_mode", "unknown")

        if email_type == "spam":
            return "忽略该邮件或加入低优先级过滤"
        if email_type == "rejection":
            return "归档该岗位邮件，停止继续跟进"
        if deadline_status == "overdue":
            return "该事项已超时，建议立即补发说明邮件并尝试电话确认"

        urgency_prefix = ""
        if deadline_status == "urgent" and deadline_hours is not None:
            urgency_prefix = f"优先处理（约 {deadline_hours} 小时内截止）："
        elif deadline_status == "soon" and deadline_hours is not None:
            urgency_prefix = f"尽快处理（约 {deadline_hours} 小时内截止）："

        if email_type == "interview":
            if interview_mode == "video":
                return urgency_prefix + "确认视频面试时间并检查会议链接，准备项目案例分享"
            if interview_mode == "phone":
                return urgency_prefix + "确认电话面试时间并保持电话畅通，准备简短自我介绍"
            return urgency_prefix + "立即确认面试安排并准备案例分享"
        if email_type == "materials":
            return urgency_prefix + "整理并提交要求材料，发送后回信确认已补交"
        if email_type == "offer":
            return urgency_prefix + "确认到岗时间与联系方式，必要时补充可入职日期"
        if email_type == "follow_up":
            return "继续等待流程更新，若 3-5 个工作日无反馈再礼貌跟进"
        return "人工查看后决定下一步"

    def classify_email(self, email):
        """邮件分类"""
        subject = email['subject'].lower()
        body = email['body'].lower()
        sender = email['sender'].lower()
        
        text_content = f"{subject} {body}"
        
        # 检查垃圾邮件
        spam_score = sum(1 for keyword in self.classification_rules['spam_keywords'] 
                        if keyword in text_content)
        if spam_score >= 2:
            return {'type': 'spam', 'priority': 'low', 'sender_type': 'external'}
        
        # 检查求职阶段常见邮件
        interview_score = sum(1 for keyword in self.classification_rules['interview_keywords'] 
                        if keyword in text_content)

        materials_score = sum(1 for keyword in self.classification_rules['materials_keywords'] 
                           if keyword in text_content)

        follow_up_score = sum(1 for keyword in self.classification_rules['follow_up_keywords'] 
                           if keyword in text_content)

        offer_score = sum(1 for keyword in self.classification_rules['offer_keywords']
                          if keyword in text_content)

        rejection_score = sum(1 for keyword in self.classification_rules['rejection_keywords']
                              if keyword in text_content)
        
        # 确定类型
        if rejection_score > 0:
            email_type = "rejection"
        elif offer_score > 0:
            email_type = "offer"
        elif follow_up_score > 0 and follow_up_score >= materials_score and follow_up_score >= interview_score:
            email_type = "follow_up"
        else:
            scores = {
            'interview': interview_score,
            'materials': materials_score,
            'follow_up': follow_up_score,
            'offer': offer_score,
            'rejection': rejection_score
            }
            email_type = max(scores, key=scores.get) if max(scores.values()) > 0 else 'other'
        
        # 确定优先级
        priority = 'high' if any(
            word in text_content for word in [
                '紧急', 'urgent', 'asap', '重要', '截止', 'deadline', 'offer', '面试'
            ]
        ) else 'medium'
        if email_type == 'spam':
            priority = 'low'
        elif email_type == 'rejection':
            priority = 'medium'
        
        # 确定发件人类型
        if any(tag in sender for tag in ['hr', 'recruit', 'talent', 'campus', 'offer']):
            sender_type = 'recruiter'
        elif 'noreply' in sender or 'no-reply' in sender:
            sender_type = 'system'
        else:
            sender_type = 'external'
        
        return {
            'type': email_type,
            'priority': priority,
            'sender_type': sender_type
        }

    def extract_info(self, email, classification=None):
        """提取关键信息"""
        if classification is None:
            classification = self.classify_email(email)

        body = email['body']
        
        # 提取日期
        date_patterns = [
            r'\d{4}-\d{1,2}-\d{1,2}',
            r'\d{1,2}\s*月\s*\d{1,2}\s*日',
            r'\d{1,2}/\d{1,2}(?:/\d{2,4})?',
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|June|July)\s+\d{1,2}(?:,\s*\d{4})?'
        ]
        
        dates = []
        for pattern in date_patterns:
            dates.extend(re.findall(pattern, body))
        dates = self.dedupe_text_list(dates)
        
        # 提取时间
        time_patterns = [
            r'\d{1,2}:\d{2}(?:\s*(?:AM|PM))?',
            r'\d{1,2}(?::\d{2})?\s*(?:AM|PM)',
            r'(?:上午|下午|中午|晚上)?\s*\d{1,2}\s*点(?:\d{1,2}分)?'
        ]
        
        times = []
        for pattern in time_patterns:
            times.extend(re.findall(pattern, body))
        times = self.dedupe_text_list(times)
        
        # 提取联系方式
        phones = re.findall(r'1[3-9]\d{9}', body)
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', body)
        
        # 提取待办事项（包含关键词的句子）
        todo_keywords = ['需要', '请', '准备', '确认', '提交', '完成', '回复', 'need', 'please', 'prepare', 'confirm', 'submit', 'complete']
        sentences = body.replace('。', '.').split('.')
        todos = []
        for sentence in sentences:
            if any(keyword in sentence for keyword in todo_keywords):
                clean_sentence = sentence.strip()
                if len(clean_sentence) > 5:
                    todos.append(clean_sentence)
        
        raw_position = self.infer_position(email, classification["type"])
        normalized_position = self.normalize_position_label(raw_position)
        deadline_raw = self.infer_deadline(body, dates, times)
        deadline_meta = self.build_deadline_meta(email, deadline_raw)

        extracted_info = {
            'dates': dates,
            'times': times,
            'phones': phones,
            'emails': emails,
            'todos': todos[:3],  # 最多3个
            'company': self.infer_company(email),
            'position': normalized_position,
            'position_raw': raw_position,
            'deadline': deadline_raw,
            'deadline_raw': deadline_meta['deadline_raw'],
            'deadline_iso': deadline_meta['deadline_iso'],
            'deadline_is_relative': deadline_meta['deadline_is_relative'],
            'deadline_hours_left': deadline_meta['deadline_hours_left'],
            'deadline_status': deadline_meta['deadline_status'],
            'interview_mode': self.infer_interview_mode(body),
            'action_suggestion': ""
        }
        extracted_info['action_suggestion'] = self.infer_action_suggestion(classification, extracted_info)
        return extracted_info

    def generate_reply(self, email, classification):
        """生成回复草稿"""
        if classification['type'] == 'spam':
            return None
        
        # 检测语言
        is_chinese = any('\u4e00' <= char <= '\u9fff' for char in email['body'])
        lang = 'zh' if is_chinese else 'en'
        
        # 选择模板
        template_type = classification['type'] if classification['type'] in ['interview', 'materials', 'offer'] else 'general'
        template = self.reply_templates[template_type][lang]
        
        # 生成回复
        reply_content = template.format(subject=email['subject'])
        
        return {
            'to': email['sender'],
            'subject': f"Re: {email['subject']}",
            'content': reply_content,
            'language': lang,
            'template_type': template_type
        }

    def run_demo(self):
        """运行演示"""
        print("🤖 求职邮件助手 - 演示版本")
        print("=" * 50)
        print(f"📧 演示邮件数量: {len(self.demo_emails)}")
        print()
        
        results = []
        stats = {'total': 0, 'classified': 0, 'replies': 0, 'reminders': 0}
        
        for i, email in enumerate(self.demo_emails, 1):
            print(f"处理邮件 {i}/{len(self.demo_emails)}: {email['subject'][:30]}...")
            
            # 分类
            classification = self.classify_email(email)
            stats['classified'] += 1
            
            # 信息提取
            extracted_info = self.extract_info(email, classification)
            
            # 生成回复
            reply = self.generate_reply(email, classification)
            if reply:
                stats['replies'] += 1
            
            # 创建提醒
            reminders = len(extracted_info['dates']) + len(extracted_info['todos'])
            stats['reminders'] += reminders
            
            results.append({
                'email': email,
                'classification': classification,
                'extracted_info': extracted_info,
                'reply': reply,
                'reminders_count': reminders
            })
        
        stats['total'] = len(self.demo_emails)
        
        print("\n✅ 处理完成！")
        self.display_results(results, stats)

    def display_results(self, results, stats):
        """显示结果"""
        print("\n📊 处理统计:")
        print(f"  总邮件数: {stats['total']}")
        print(f"  已分类: {stats['classified']}")
        print(f"  生成回复: {stats['replies']}")
        print(f"  创建提醒: {stats['reminders']}")
        
        # 分类统计
        types = [r['classification']['type'] for r in results]
        priorities = [r['classification']['priority'] for r in results]
        
        print("\n📋 分类统计:")
        type_counts = Counter(types)
        for email_type, count in type_counts.items():
            print(f"  {email_type}: {count}")
        
        print("\n⚡ 优先级统计:")
        priority_counts = Counter(priorities)
        for priority, count in priority_counts.items():
            print(f"  {priority}: {count}")
        
        print("\n📝 处理结果样例:")
        print("-" * 50)
        
        for i, result in enumerate(results[:3], 1):  # 显示前3个
            email = result['email']
            classification = result['classification']
            extracted = result['extracted_info']
            reply = result['reply']
            
            print(f"\n邮件 {i}:")
            print(f"  主题: {email['subject']}")
            print(f"  发件人: {email['sender']}")
            print(f"  分类: {classification['type']} | 优先级: {classification['priority']}")
            
            if extracted['dates']:
                print(f"  关键日期: {', '.join(extracted['dates'])}")
            if extracted['times']:
                print(f"  时间: {', '.join(extracted['times'])}")
            print(f"  公司: {extracted['company']}")
            print(f"  岗位: {extracted['position']}")
            if extracted['position_raw'] != extracted['position']:
                print(f"  岗位原文: {extracted['position_raw']}")
            print(f"  截止节点: {extracted['deadline_raw']}")
            if extracted['deadline_iso'] != "未识别":
                print(f"  截止标准化: {extracted['deadline_iso']} ({extracted['deadline_status']})")
            print(f"  面试形式: {extracted['interview_mode']}")
            if extracted['todos']:
                print(f"  待办: {extracted['todos'][0][:50]}...")
            print(f"  行动建议: {extracted['action_suggestion']}")
            
            if reply:
                print(f"  回复草稿 ({reply['language']}): {reply['content'][:80]}...")
            
            print(f"  提醒数量: {result['reminders_count']}")
        
        print("\n🎉 演示完成！")
        print("\n💡 下一步:")
        print("1. 继续完善求职场景模板与样例数据")
        print("2. 配置真实邮箱请编辑: config/email_config.json")
        print("3. 如需完整实验可再迁移到 notebook 版本")

if __name__ == "__main__":
    demo = EmailDemo()
    demo.run_demo()
