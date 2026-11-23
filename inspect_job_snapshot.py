"""离线检查从浏览器复制的职位页。输入是首行 URL 加 HTML 的本地文件。"""

import argparse
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from lxml import etree, html

from src.jobsdb import snapshot as jobsdb
from src.linkedin import snapshot as linkedin
from src.utils.job import Job


def inspect_snapshot(path: Path) -> list[Job]:
    address, _, markup = path.read_text(encoding="utf-8-sig").partition("\n")
    page = urlsplit(address.strip())
    if not markup.strip():
        raise ValueError("首行填写页面 URL，第二行起放置复制的元素 HTML。")
    parser = html.HTMLParser(no_network=True)
    root = html.fragment_fromstring(markup, create_parent="div", parser=parser)
    if page.hostname == "hk.jobsdb.com":
        return jobsdb.read_jobs(root)
    if page.hostname in {"www.linkedin.com", "linkedin.com"}:
        selected = parse_qs(page.query).get("currentJobId", [""])[0]
        return linkedin.read_jobs(root, selected)
    raise ValueError("首行 URL 的域名与已支持的平台不匹配。")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="包含页面地址和元素的 Markdown 文件")
    parser.add_argument("--list", action="store_true", help="同时列出职位 ID、标题、公司和地点")
    args = parser.parse_args()
    try:
        jobs = inspect_snapshot(args.snapshot)
    except (OSError, ValueError, etree.ParserError) as exc:
        parser.exit(1, f"读取失败：{exc}\n")
    print(f"唯一职位 {len(jobs)} 个，含详情区正文 {sum(bool(job.description) for job in jobs)} 个")
    if args.list:
        for job in jobs:
            job_id = job.get_platform_data("job_id")
            print(f"{job_id}\t{job.title}\t{job.company}\t{job.location}")


if __name__ == "__main__":
    main()
