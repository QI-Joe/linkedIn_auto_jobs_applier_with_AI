"""根据本地页面样本、CV 及确认过的偏好准备材料；默认止于人工审阅。"""

import argparse
import json
import subprocess
import tempfile
from datetime import date
from functools import partial
from pathlib import Path

import yaml
from lxml import etree

from inspect_job_snapshot import inspect_snapshot
from src.jobsdb.preparation import read_detail, rehearse
from src.linkedin.snapshot import read_easy_apply_capture
from src.preparation.matching import confirmed_answers, cv_facts, daily_ranking, evaluate, read_mapping
from src.preparation.materials import digest, prepare_version, write_json


def recommended_questions(job, confirmed, attachments):
    questions = []
    for prompt in job.get_platform_data("application_fields", []):
        value = confirmed.get(prompt)
        if isinstance(value, dict):
            value = value["value"]
        questions.append({"question": prompt, "answer": value,
                          "source": "confirmed_profile" if value else "needs_confirmation"})
    return {"questions": questions, "steps": [], "status": "recommended", "issues": []}


def run(args):
    cv = read_mapping(args.cv)
    profile = read_mapping(args.profile)
    facts = cv_facts(cv)
    cv_hash = digest(args.cv)
    day_dir = args.output.resolve() / args.day.isoformat()
    summary = {"day": args.day.isoformat(), "mode": args.mode, "submitted": False}
    confirmed = confirmed_answers(profile)
    if args.mode == "jobsdb":
        job = read_detail(args.detail)
        match, fact = evaluate(job, profile, facts)
        apply_key = f"{job.platform}/{job.get_platform_data('job_id')}"
        if match["excluded"] or apply_key in profile.get("applied", {}):
            raise ValueError("该职位已排除或已标记申请，停止材料准备")


        selected = [(job, match, fact)]
    else:
        jobs = inspect_snapshot(args.snapshot)
        if any(job.platform != "linkedin" for job in jobs):
            raise ValueError("recommend 需要 LinkedIn 搜索页样本")
        if args.easy_apply_steps:
            capture = read_easy_apply_capture(args.easy_apply_steps)
            unique = {j.get_platform_data("job_id"): j for j in jobs}
            job_id = capture.get_platform_data("job_id")
            prior = unique.get(job_id)
            if prior and (prior.title, prior.company) != (capture.title, capture.company):
                raise ValueError("两个 LinkedIn 样本中的同 ID 职位身份冲突")
            if prior and prior.apply_method == "Applied":
                capture.apply_method = "Applied"
            unique[job_id] = capture
            jobs = list(unique.values())
        remaining, pool, selected = daily_ranking(jobs, profile, facts, args.day, args.target, args.top)
        summary.update(daily_target=args.target, remaining=remaining, priority_limit=args.top,
                       candidate_ids=[job.get_platform_data("job_id") for job, _, _ in pool])


    packages = []
    summary["results"] = []
    summary["errors"] = []
    for job, match, fact in selected:
        if args.mode == "jobsdb":
            review = partial(rehearse, job, args.steps, confirmed)
        else:
            review = partial(recommended_questions, job, confirmed)
        try:
            version = prepare_version(args.output.resolve(), args.day, job, match, fact, args.resume.resolve(),
                                      cv_hash, args.office, review)
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            # 同一批次已生成的版本仍需可追溯；转换环境故障时停止继续生成。
            summary["errors"].append({"job_id": job.get_platform_data("job_id"), "stage": "preparation",
                                      "reason": str(exc)})
            break
        package = str(version.relative_to(day_dir))
        packages.append(package)
        manifest = json.loads((version / "manifest.json").read_text())
        summary["results"].append({
            "rank": len(packages), "package": package, "title": job.title, "company": job.company,
            "job_url": job.link, "apply_url": manifest["apply_url"], "apply_method": manifest["apply_method"],
            "score": match["score"], "reasons": match["reasons"], "requirements": match["requirements"],
            "warnings": match["warnings"] + manifest["issues"], "status": manifest["status"],
            "submitted": False,
        })
    day_dir.mkdir(parents=True, exist_ok=True)
    summary["packages"] = packages
    # 保存每次推荐的输入目标及具体版本，重跑不会覆盖已经审阅过的清单。
    with tempfile.NamedTemporaryFile(dir=day_dir, prefix=".draft-", delete=False) as draft:
        path = Path(draft.name)
    try:
        write_json(path, summary)
        result = day_dir / (args.mode + "-" + path.name.removeprefix(".draft-") + ".json")
        path.rename(result)
    finally:
        path.unlink(missing_ok=True)
    return result, summary["errors"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--cv", type=Path, required=True, help="结构化 CV YAML")
    common.add_argument("--profile", type=Path, required=True, help="偏好和已核实问答 YAML")
    common.add_argument("--resume", type=Path, required=True, help="用于申请的 PDF 或 DOCX 原件")
    common.add_argument("--day", type=date.fromisoformat, default=date.today(), help="材料日期 YYYY-MM-DD")
    common.add_argument("--output", type=Path, default=Path("data_folder/output"))
    common.add_argument("--office", default="soffice", help="LibreOffice 可执行文件")
    jd = modes.add_parser("jobsdb", parents=[common], help="演练一个 JobsDB Quick Apply")
    jd.add_argument("--detail", required=True, type=Path)
    jd.add_argument("--steps", required=True, type=Path, help="包含 step1 至 step4 的本地目录")
    li = modes.add_parser("recommend", parents=[common], help="准备 LinkedIn 每日优先推荐")
    li.add_argument("--snapshot", required=True, type=Path)
    li.add_argument("--easy-apply-steps", type=Path, help="可选的四步站内弹窗样本目录")
    li.add_argument("--target", type=int, default=20)
    li.add_argument("--top", type=int, default=5)
    args = parser.parse_args()
    try:
        result, errors = run(args)
    except (ValueError, OSError, subprocess.SubprocessError, etree.ParserError, yaml.YAMLError) as exc:
        parser.exit(1, f"准备失败：{exc}\n")
    print(f"本地准备结果：{result}")
    if errors:
        parser.exit(1, f"准备未完成：{errors[0]['reason']}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
