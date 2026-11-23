"""用本地履历证据和显式偏好解释排序；推荐结果没有投递副作用。"""

import re
from dataclasses import dataclass
from datetime import date

import yaml


def read_mapping(path):
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        # YAML 异常默认带有原文，履历或答案不应出现在控制台日志中。
        raise ValueError(f"{path.name} 的 YAML 格式无效") from None
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} 须包含 YAML 映射")
    return data


def confirmed_answers(profile):
    answers = profile.get("answers", {})
    facts = profile.get("facts", {})
    if not isinstance(answers, dict) or not isinstance(facts, dict):
        raise ValueError("answers 和 facts 须为映射")
    resolved = {}
    for question, answer in answers.items():
        if not isinstance(question, str):
            raise ValueError("answers 的键须为题干文字")
        if isinstance(answer, dict):
            key = answer.get("fact")
            if not isinstance(key, str):
                raise ValueError("答案引用须包含明确的 fact 键")
            resolved[question] = {"fact": key, "value": facts.get(key)}
        else:
            resolved[question] = answer
    return resolved


def strings(values, name):
    if not isinstance(values, list) or not all(isinstance(v, str) and v.strip() for v in values):
        raise ValueError(f"{name} 须为非空字符串组成的列表")
    return list(dict.fromkeys(v.strip() for v in values))


def contains(text, term):
    # 防止 AI 匹配到 training 中间，同时允许 C++、短语和中文关键词。
    pattern = re.escape(term.strip())
    if term.isascii():
        pattern = r"(?<![a-z0-9])" + pattern + r"(?![a-z0-9])"
    return bool(re.search(pattern, text, re.I))


@dataclass(frozen=True)
class Fact:
    context: str
    text: str
    source: str


def cv_facts(cv):
    facts = []
    for key in ("projects", "experience_details"):
        rows = cv.get(key, [])
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise ValueError(f"CV 的 {key} 须为记录列表")
    for i, project in enumerate(cv.get("projects", [])):
        if isinstance(project.get("description"), str) and project["description"].strip():
            facts.append(Fact(str(project.get("name", "Project")), project["description"],
                              f"projects[{i}].description"))
    for i, exp in enumerate(cv.get("experience_details", [])):
        responsibilities = exp.get("key_responsibilities", [])
        if not isinstance(responsibilities, list):
            raise ValueError("CV 的 key_responsibilities 须为列表")
        for j, responsibility in enumerate(responsibilities):
            values = responsibility.values() if isinstance(responsibility, dict) else [responsibility]
            for value in values:
                if isinstance(value, str) and value.strip():
                    facts.append(Fact(str(exp.get("position", "Experience")), value,
                                      f"experience_details[{i}].key_responsibilities[{j}]"))
    if not facts:
        raise ValueError("CV 缺少可引用的 projects[].description 或工作经历 key_responsibilities")
    return facts


def evaluate(job, profile, facts):
    prefs = {key: strings(profile.get(key, []), key)
             for key in ("positions", "locations", "skills", "excluded_companies", "excluded_titles", "required_locations")}
    reasons, warnings = [], []
    rejected = job.company.casefold() in {s.casefold() for s in prefs["excluded_companies"]}
    rejected |= any(contains(job.title, s) for s in prefs["excluded_titles"])
    requirements = job.get_platform_data("requirements", [])
    evidence_text = " ".join([job.title, job.description, job.get_platform_data("summary", "")])
    skills = [s for s in prefs["skills"] if contains(evidence_text, s)
              and any(contains(f.text, s) for f in facts)]
    roles = [s for s in prefs["positions"] if contains(job.title, s)]
    locations = [s for s in prefs["locations"] if contains(job.location, s)]
    if roles:
        reasons.append("职位名称符合偏好：" + "、".join(roles))
    if locations:
        reasons.append("地点符合偏好：" + "、".join(locations))
    if skills:
        reasons.append("岗位及履历均有证据：" + "、".join(skills))
    if prefs["required_locations"]:
        if job.location and not any(contains(job.location, place) for place in prefs["required_locations"]):
            rejected = True
            warnings.append("地点与用户的硬性限制冲突")
        elif not job.location:
            warnings.append("职位地点未知，需人工确认硬性限制")
    if job.get_platform_data("review_unverified"):
        warnings.append("Easy Apply 样本的完整审阅字段未验证")
    if not requirements:
        warnings.append("缺少明确的任职要求，需核对详情")
    if not job.apply_method:
        warnings.append("申请方式未披露")
    if job.apply_method == "External":
        warnings.append("外部申请表与必填字段尚未核实")
    if not job.company or not job.title:
        rejected = True
        warnings.append("缺少公司或职位名称")
    if rejected:
        warnings.append("排除或身份条件未通过")
    if not skills:
        warnings.append("未找到岗位技能与 CV 经历的直接交集")
    ranked = sorted(facts, key=lambda f: sum(contains(f.text, s) for s in skills), reverse=True)
    fact = ranked[0]
    score = 4 * bool(roles) + 2 * bool(locations) + min(4, len(skills))
    fit = "不适合" if rejected else "需人工确认"
    if not rejected and skills and requirements and not warnings:
        fit = "建议优先审阅"
    return {"score": score, "assessment": fit, "role_match": bool(roles), "reasons": reasons, "warnings": warnings, "excluded": rejected,
            "requirements": requirements, "skills": skills, "cv_source": fact.source}, fact


def daily_ranking(jobs, profile, facts, day: date, target: int, priority: int):
    if target < 1 or priority < 1:
        raise ValueError("每日目标和优先推荐数均须大于零")
    applied = profile.get("applied", {})
    if not isinstance(applied, dict):
        raise ValueError("applied 须为 平台/职位ID 到申请日期的映射")
    for value in applied.values():
        date.fromisoformat(str(value))
    remaining = max(0, target - sum(str(v) == day.isoformat() for v in applied.values()))
    ranked = []
    for job in jobs:
        key = f"{job.platform}/{job.get_platform_data('job_id')}"
        if key in applied or job.apply_method == "Applied":
            continue
        match, fact = evaluate(job, profile, facts)
        if not match["excluded"] and (match["skills"] or match["role_match"]):
            ranked.append((job, match, fact))
    ranked.sort(key=lambda row: (-row[1]["score"], -bool(row[1]["requirements"]),
                                 row[0].get_platform_data("job_id")))
    pool = ranked[:remaining]
    return remaining, pool, pool[:priority]
