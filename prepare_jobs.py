"""根据本地页面样本、CV 及确认过的偏好准备材料；默认止于人工审阅。"""

import argparse
import json
import sqlite3
import subprocess
import tempfile
from datetime import date
from functools import partial
from pathlib import Path

import yaml
from lxml import etree

from inspect_job_snapshot import inspect_snapshot
from src.preparation.collect import collect
from src.preparation.history import DEFAULT_HISTORY, JobHistory, onsite_eligible
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
    history = JobHistory(args.history)
    if args.mode == "jobsdb":
        job = read_detail(args.detail)
        history.save([job], "snapshot-detail")
    else:
        if args.snapshot:
            history.save(inspect_snapshot(args.snapshot), "snapshot-list")
        if args.easy_apply_steps:
            history.save([read_easy_apply_capture(args.easy_apply_steps)], "snapshot-easy-apply")

    cv = read_mapping(args.cv)
    profile = read_mapping(args.profile)
    facts = cv_facts(cv)
    cv_hash = digest(args.cv)
    day_dir = args.output.resolve() / args.day.isoformat()
    summary = {"day": args.day.isoformat(), "mode": args.mode, "submitted": False}
    confirmed = confirmed_answers(profile)
    if args.mode == "jobsdb":
        stored = history.get(job.platform, job.get_platform_data("job_id"))
        if not onsite_eligible(job) or not onsite_eligible(stored):
            raise ValueError("该职位已归档，当前不能进入 JobsDB Quick Apply")
        match, fact = evaluate(job, profile, facts)
        apply_key = f"{job.platform}/{job.get_platform_data('job_id')}"
        if match["excluded"] or apply_key in profile.get("applied", {}):
            raise ValueError("该职位已排除或已标记申请，停止材料准备")
        selected = [(job, match, fact)]
    else:
        remaining, pool, selected = daily_ranking(history.jobs(), profile, facts, args.day, args.target, args.top)
        summary.update(daily_target=args.target, remaining=remaining, priority_limit=args.top,
                       candidate_ids=[j.get_platform_data("job_id") for j, _, _ in pool],
                       candidate_keys=[f"{j.platform}/{j.get_platform_data('job_id')}" for j, _, _ in pool])
        summary["recommendations"] = [
            {"rank": rank, "platform": j.platform, "job_id": j.get_platform_data("job_id"),
             "title": j.title, "company": j.company, "job_url": j.link, "apply_method": j.apply_method,
             "onsite_eligible": onsite_eligible(j), "score": match["score"],
             "reasons": match["reasons"], "warnings": match["warnings"]}
            for rank, (j, match, _) in enumerate(selected, 1)
        ]

    packages = []
    summary["results"] = []
    summary["errors"] = []
    for rank, (job, match, fact) in enumerate(selected, 1):
        if not args.resume or not onsite_eligible(job):
            continue
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
        package = version.relative_to(day_dir).as_posix()
        packages.append(package)
        manifest = json.loads((version / "manifest.json").read_text(encoding="utf-8"))
        summary["results"].append({
            "rank": rank, "package": package, "title": job.title, "company": job.company,
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
    common.add_argument("--history", type=Path, default=DEFAULT_HISTORY, help="本机职位历史库")
    common.add_argument("--day", type=date.fromisoformat, default=date.today(), help="材料日期 YYYY-MM-DD")
    common.add_argument("--output", type=Path, default=Path("data_folder/output"))
    common.add_argument("--office", default="soffice", help="LibreOffice 可执行文件")
    jd = modes.add_parser("jobsdb", parents=[common], help="演练一个 JobsDB Quick Apply")
    jd.add_argument("--resume", required=True, type=Path)
    jd.add_argument("--detail", required=True, type=Path)
    jd.add_argument("--steps", required=True, type=Path, help="包含 step1 至 step4 的本地目录")
    li = modes.add_parser("recommend", parents=[common], help="使用两平台的历史职位生成推荐")
    li.add_argument("--snapshot", type=Path, help="可选，先导入本次搜索页")
    li.add_argument("--resume", type=Path, help="指定后为已确认站内申请的推荐职位生成材料")
    li.add_argument("--easy-apply-steps", type=Path, help="可选的四步站内弹窗样本目录")
    li.add_argument("--target", type=int, default=20)
    li.add_argument("--top", type=int, default=5)
    ingest = modes.add_parser("collect", help="只读采集或导入职位，用于今后推荐")
    ingest.add_argument("--url", action="append", default=[], help="浏览器读取的搜索页地址，可重复")
    ingest.add_argument("--browser-profile", type=Path, help="本机 Chrome 专用用户目录")
    ingest.add_argument("--snapshot", action="append", type=Path, default=[], help="已保存的列表快照，可重复")
    ingest.add_argument("--detail", action="append", type=Path, default=[], help="JobsDB 详情，可重复")
    ingest.add_argument("--easy-apply-steps", type=Path, help="可选的 LinkedIn 站内弹窗样本目录")
    ingest.add_argument("--legacy-log", action="append", type=Path, default=[], help="旧 JobsDB 日志文件或含 *_log.json 的目录，可重复")
    ingest.add_argument("--history", type=Path, default=DEFAULT_HISTORY)
    archive = modes.add_parser("history", help="查看已归档的职位和公司描述")
    archive.add_argument("--history", type=Path, default=DEFAULT_HISTORY)
    archive.add_argument("--platform", choices=["jobsdb", "linkedin"])
    archive.add_argument("--job-id", help="与平台一起使用，显示该职位完整记录")
    args = parser.parse_args()
    try:
        if args.mode == "history":
            if args.job_id and not args.platform:
                parser.error("--job-id 需要同时指定 --platform")
            history = JobHistory(args.history)
            if args.job_id:
                job = history.get(args.platform, args.job_id)
                if not job:
                    raise ValueError("职位库中未找到该平台与职位 ID")
                print(json.dumps(job.to_dict(), ensure_ascii=False, indent=2))
            else:
                for job in history.jobs():
                    if not args.platform or job.platform == args.platform:
                        job_id = job.get_platform_data("job_id")
                        print(f"{job.platform}/{job_id}\t{job.title}\t{job.company}\t{job.apply_method or 'Unknown'}")
            return 0
        if args.mode == "collect":
            collect(args, JobHistory(args.history))
            return 0
        result, errors = run(args)
    except (ValueError, OSError, sqlite3.Error, subprocess.SubprocessError, etree.ParserError, yaml.YAMLError) as exc:
        parser.exit(1, f"准备失败：{exc}\n")
    print(f"本地准备结果：{result}")
    if errors:
        parser.exit(1, f"准备未完成：{errors[0]['reason']}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
