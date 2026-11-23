"""按平台和职位 ID 维护本地档案，保留每一版不同的观察内容。"""

import json
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from src.utils.job import Job, unidentified_card


DEFAULT_HISTORY = Path("data_folder/job_history.sqlite3")


def onsite_eligible(job):
    expected = {"jobsdb": "Quick Apply", "linkedin": "Easy Apply"}
    if job.platform not in expected or job.apply_method != expected[job.platform]:
        return False
    job_id = job.get_platform_data("job_id", "")
    if not re.fullmatch(r"[0-9]+", job_id):
        return False
    if job.platform == "jobsdb":
        base = f"https://hk.jobsdb.com/job/{job_id}"
        destinations = {base + "/apply"}
    else:
        base = f"https://www.linkedin.com/jobs/view/{job_id}"
        destinations = {base}
    dest = job.get_platform_data("apply_url") or ""
    if dest:
        address = urlsplit(dest)
        clean = address._replace(query="", fragment="").geturl().rstrip("/")
        if clean not in destinations:
            return False
    return job.link.rstrip("/") == base


class JobHistory:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (
                    platform TEXT NOT NULL, job_id TEXT NOT NULL, data TEXT NOT NULL,
                    first_seen TEXT NOT NULL, last_seen TEXT NOT NULL,
                    PRIMARY KEY (platform, job_id)
                );
                CREATE TABLE IF NOT EXISTS observations (
                    platform TEXT NOT NULL, job_id TEXT NOT NULL, source TEXT NOT NULL,
                    observed_at TEXT NOT NULL, data TEXT NOT NULL,
                    UNIQUE (platform, job_id, source, data)
                );
            """)

    def connect(self):
        return sqlite3.connect(self.path, timeout=20)

    def save(self, jobs, source, observed_at=None):
        """同批读卡先提交；空字段不冲掉详情，较旧记录只补缺。"""
        stamp = observed_at or datetime.now(timezone.utc).isoformat()
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            for job in jobs:
                job_id = job.get_platform_data("job_id", "")
                if job.platform not in {"jobsdb", "linkedin"} or not re.fullmatch(r"[0-9]+|unidentified-[0-9a-f]{64}", job_id):
                    raise ValueError("职位缺少可归档的平台或数字 ID")
                key = (job.platform, job_id)
                incoming = job.to_dict()
                encoded = json.dumps(incoming, ensure_ascii=False, sort_keys=True)
                db.execute("INSERT OR IGNORE INTO observations VALUES (?,?,?,?,?)",
                           (*key, source, stamp, encoded))
                row = db.execute("SELECT data, last_seen FROM jobs WHERE platform=? AND job_id=?", key).fetchone()
                current = json.loads(row[0]) if row else {}
                if source == "snapshot-easy-apply" and any(
                    current.get(field) and current[field] != incoming[field] for field in ("title", "company")
                ):
                    raise ValueError("LinkedIn 同 ID 职位的名称或公司冲突")
                newer = not row or stamp >= row[1]
                merged = self.merge(current, incoming, newer)
                if current.get("apply_method") == "External" and merged["apply_method"] == "Easy Apply":
                    if source in {"snapshot-list", "browser-list", "snapshot-easy-apply"}:
                        merged["apply_method"] = "External"
                        merged["platform_specific_data"]["apply_url"] = current["platform_specific_data"].get("apply_url")
                db.execute("""
                    INSERT INTO jobs VALUES (?,?,?,?,?)
                    ON CONFLICT(platform, job_id) DO UPDATE SET
                        data=excluded.data, first_seen=min(first_seen,excluded.first_seen),
                        last_seen=max(last_seen,excluded.last_seen)
                """, (*key, json.dumps(merged, ensure_ascii=False), stamp, stamp))

    @staticmethod
    def merge(previous, incoming, newer):
        result = dict(previous)
        details = dict(result.get("platform_specific_data", {}))
        for name, value in incoming.items():
            if name != "platform_specific_data" and value and (newer or not result.get(name)):
                result[name] = value
            elif name not in result:
                result[name] = value
        for name, value in incoming["platform_specific_data"].items():
            if value and (newer or not details.get(name)):
                details[name] = value
        if previous.get("apply_method") == "Applied" or incoming["apply_method"] == "Applied":
            result["apply_method"] = "Applied"
        result["platform_specific_data"] = details
        return result

    def get(self, platform, job_id):
        with closing(self.connect()) as db:
            row = db.execute("SELECT data FROM jobs WHERE platform=? AND job_id=?",
                             (platform, job_id)).fetchone()
        return Job(**json.loads(row[0])) if row else None

    def jobs(self):
        with closing(self.connect()) as db:
            return [Job(**json.loads(data)) for (data,) in db.execute(
                "SELECT data FROM jobs ORDER BY platform, job_id")]


def legacy_job(row):
    """旧 JobsDB 日志混有翻页事件，仅转换带职位身份的记录。"""
    info = row.get("job_info", row)
    if not isinstance(info, dict) or not any(info.get(k) for k in ("job_id", "title", "detailed_page")):
        return None
    job_id = str(info.get("job_id", ""))
    base = ""
    if re.fullmatch(r"[0-9]+", job_id):
        base = f"https://hk.jobsdb.com/job/{job_id}"
    else:
        identity = [info.get(k) for k in ("title", "company", "location", "detailed_page")]
        job_id = unidentified_card(json.dumps(identity, sort_keys=True, ensure_ascii=False))
    sections = info.get("detailed_page") or {}
    description = sections if isinstance(sections, str) else "\n".join(
        f"{key}\n{value}" for key, value in sections.items())
    method = info.get("apply_button_type") or row.get("button_type") or ""
    if info.get("applied") is True or row.get("applied") is True or row.get("submitted") is True:
        method = "Applied"
    elif method.strip().casefold() == "quick apply":
        method = "Quick Apply"
    return Job(info.get("title", ""), info.get("company", ""), info.get("location", ""),
               base, method, platform="jobsdb", description=info.get("description") or description,
               salary=info.get("salary", ""), job_type=info.get("work_style", ""),
               platform_specific_data={"job_id": job_id, "sections": sections})
