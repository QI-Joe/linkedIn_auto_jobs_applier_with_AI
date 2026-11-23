"""读取用户从 JobsDB 搜索页复制的列表 HTML。"""

from lxml.html import HtmlElement

from src.utils.job import Job


def _field(card: HtmlElement, name: str) -> str:
    return card.xpath('normalize-space(.//*[@data-automation=$key][1])', key=name)


def read_jobs(root: HtmlElement) -> list[Job]:
    cards = root.xpath('.//article[@data-testid="job-card"]')
    if not cards:
        raise ValueError("没有找到 JobsDB 职位卡片，请检查复制的范围或页面结构。")

    jobs = []
    seen = set()
    for card in cards:
        job_id = card.get("data-job-id", "")
        if not job_id.isascii() or not job_id.isdecimal() or job_id in seen:
            continue
        seen.add(job_id)
        # 列表只披露职位摘要；完整正文须在对应详情页上另行读取。
        jobs.append(Job(
            title=_field(card, "jobTitle"),
            company=_field(card, "jobCompany"),
            location=_field(card, "jobLocation"),
            link=f"https://hk.jobsdb.com/job/{job_id}",
            apply_method="",
            platform="jobsdb",
            salary=_field(card, "jobSalary"),
            date_posted=_field(card, "jobListingDate"),
            platform_specific_data={"job_id": job_id, "summary": _field(card, "jobShortDescription")},
        ))
    return jobs
