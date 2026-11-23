"""读取 LinkedIn 搜索页快照中的职位和当前选中的详情。"""

from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit

from lxml import html

from lxml.html import HtmlElement

from src.utils.job import Job, unidentified_card


def class_text(element, name):
    matches = element.find_class(name)
    return " ".join(matches[0].text_content().split()) if len(matches) == 1 else ""


def public_cards(results):
    jobs = {}
    for item in results.xpath("./li"):
        cards = item.find_class("base-card")
        if not cards:
            continue
        card = cards[0]
        text = " ".join(card.text_content().split())
        identity = re.fullmatch(r"urn:li:jobPosting:([0-9]+)", card.get("data-entity-urn", ""))
        job_id = identity[1] if identity else unidentified_card(text)
        dates = card.xpath(".//time/@datetime")
        jobs[job_id] = Job(
            class_text(card, "base-search-card__title"), class_text(card, "base-search-card__subtitle"),
            class_text(card, "job-search-card__location"),
            f"https://www.linkedin.com/jobs/view/{job_id}/" if identity else "", "",
            date_posted=dates[0] if dates else "",
            platform_specific_data={"job_id": job_id, "card_text": text, "listing_layout": "public"},
        )
    if not jobs:
        raise ValueError("LinkedIn 公开列表中未识别到职位卡片")
    return list(jobs.values())


def public_detail(root, url, card):
    """访客详情按地址的职位 ID、标题和公司核对；缺少明确按钮时仅保存。"""
    job_id = card.get_platform_data("job_id")
    path = urlsplit(url).path
    match = re.fullmatch(r"/jobs/view/(?:[^/]+-)?([0-9]+)/?", path)
    if not match or match[1] != job_id:
        return None
    title = class_text(root, "top-card-layout__title")
    company = class_text(root, "topcard__org-name-link")
    bodies = root.find_class("description__text")
    description = class_text(bodies[0], "show-more-less-html__markup") if len(bodies) == 1 else ""
    if title != card.title or company != card.company or not description:
        return None
    return Job(title, company, card.location, card.link, card.apply_method, description=description,
               date_posted=card.date_posted, platform_specific_data=dict(card.platform_specific_data))


def read_jobs(root: HtmlElement, selected_id: str = "") -> list[Job]:
    columns = root.xpath('.//*[@componentkey="SearchResultsMainContent"]')
    if not columns:
        public = root.find_class("jobs-search__results-list")
        if len(public) == 1:
            return public_cards(public[0])
    if len(columns) != 1:
        raise ValueError("缺少唯一的 LinkedIn 搜索结果区 SearchResultsMainContent。")
    # 同一 ID 出现在卡片的内外两层，只读取具有交互语义的外层。
    cards = columns[0].xpath('.//*[@role="button" and starts-with(@componentkey,"job-card-component-ref-")]')
    if not cards:
        raise ValueError("已找到 LinkedIn 结果区，未找到可识别的职位卡片。")

    jobs = {}
    for card in cards:
        job_id = card.get("componentkey").removeprefix("job-card-component-ref-")
        card_text = " ".join(card.itertext()).strip()
        identified = job_id.isascii() and job_id.isdecimal()
        if not identified:
            job_id = unidentified_card(card_text)
        if job_id in jobs:
            continue
        # 首段同时含无障碍朗读标题和显示标题，后者不附带“已选中”等状态文字。
        title = company = location = ""
        titles = card.xpath('(.//p)[1]/span[@aria-hidden="true"][1]')
        if titles:
            label = titles[0]
            title = label.xpath("normalize-space(.)")
            company = label.xpath("normalize-space(../../following-sibling::div[1]/p)")
            location = label.xpath("normalize-space(../../../p)")

        labels = {p.text_content().strip() for p in card.iter("p")}
        method = ""
        if "Applied" in labels:
            method = "Applied"
        elif "Easy Apply" in labels:
            method = "Easy Apply"
        jobs[job_id] = Job(
            title=title,
            company=company,
            location=location,
            link=f"https://www.linkedin.com/jobs/view/{job_id}/" if identified else "",
            apply_method=method,
            platform="linkedin",
            platform_specific_data={"job_id": job_id, "card_text": card_text},
        )

    # 侧栏只有当前选中的职位。用详情链接复核页面 URL 中的 ID，避免给整页卡片复制同一份正文。
    if selected_id in jobs:
        detail_links = root.xpath('.//a[contains(@href,"/jobs/view/")]/@href')
        paths = {urlsplit(link).path.rstrip("/") for link in detail_links}
        descriptions = root.xpath('.//h2[normalize-space(.)="About the job"]/../..//*[@data-testid="expandable-text-box"]')
        if paths == {f"/jobs/view/{selected_id}"} and len(descriptions) == 1:
            job = jobs[selected_id]
            description = descriptions[0]
            job.description = " ".join(description.itertext()).strip()
            for group in description.xpath(".//ul|.//ol"):
                heading = group.xpath("normalize-space(preceding-sibling::text()[normalize-space()][1])")
                if heading.casefold().replace("’", "'") in {"what we're looking for", "requirements", "qualifications"}:
                    job.platform_specific_data["requirements"] = [
                        item.text_content().strip() for item in group.xpath("./li")
                    ]
                    break
            # 另一份详情使用加粗标题和编号段落，按标题范围收集要求。
            if not job.get_platform_data("requirements"):
                requirements = []
                in_requirements = False
                for element in description:
                    if element.tag == "p" and element.xpath("./strong|./b"):
                        heading = element.text_content().strip().casefold()
                        in_requirements = heading in {"requirements", "professional knowledge", "qualifications"}
                    elif in_requirements and element.tag == "p":
                        text = element.text_content().strip()
                        if text:
                            requirements.append(text)
                    elif in_requirements and element.tag in {"ul", "ol"}:
                        requirements.extend(li.text_content().strip() for li in element.xpath("./li"))
                job.platform_specific_data["requirements"] = requirements
        if paths == {f"/jobs/view/{selected_id}"}:
            job = jobs[selected_id]
            company_text = root.xpath(
                './/h2[normalize-space(.)="About the company"]/../..//*[@data-testid="expandable-text-box"]'
            )
            if len(company_text) == 1:
                job.set_platform_data("company_description", " ".join(company_text[0].itertext()).strip())
            links = root.xpath('.//a[@aria-label="Apply on company website"]/@href')
            if links and job.apply_method != "Applied":
                job.apply_method = "External"
            if len(links) == 1:
                url = urlsplit(links[0])
                destination = links[0]
                if url.path == "/safety/go/" and url.hostname in {None, "www.linkedin.com", "linkedin.com"}:
                    destination = parse_qs(url.query).get("url", [""])[0]
                target = urlsplit(destination)
                if target.scheme in {"http", "https"} and target.hostname and not target.username and not target.password:
                    job.platform_specific_data["apply_url"] = destination
                    if job.apply_method != "Applied":
                        job.apply_method = "External"
    return list(jobs.values())

def read_easy_apply_capture(directory: Path):
    """核对联系方式、简历选择、审阅片段与历史提示，不读取个人字段值。"""
    job = None
    prompts = []
    for step in range(1, 5):
        path = directory / f"easy_apply_step{step}.md"
        root = html.fragment_fromstring(path.read_text(encoding="utf-8"), create_parent="div",
                                        parser=html.HTMLParser(no_network=True))
        if step in {1, 2}:
            ids = set()
            for href in root.xpath('.//a[contains(@href,"/jobs/view/")]/@href'):
                match = re.fullmatch(r"/jobs/view/([0-9]+)/?", urlsplit(href).path)
                if match:
                    ids.add(match[1])
            dialogs = root.xpath('.//*[@data-testid="dialog"]')
            if len(ids) != 1 or len(dialogs) != 1:
                raise ValueError(f"LinkedIn 第 {step} 步无唯一的职位详情或弹窗")
            job_id = ids.pop()
            dialog = dialogs[0]
            if step == 1:
                job = next((j for j in read_jobs(root, job_id)
                            if j.get_platform_data("job_id") == job_id), None)
                if not job or not dialog.xpath('.//input[@type="tel"]') or not dialog.xpath('.//button[normalize-space(.)="Next"]'):
                    raise ValueError("LinkedIn 联系方式步骤缺失或职位身份不明")
                prompts.extend(label.text_content().strip().rstrip("*") for label in dialog.xpath(".//label"))
            elif job_id != job.get_platform_data("job_id") or not dialog.xpath('.//button[normalize-space(.)="Upload resume"]'):
                raise ValueError("LinkedIn 简历步骤缺失或职位不一致")
        elif step == 3 and not root.xpath('.//*[normalize-space(.)="Submit application"]'):
            raise ValueError("LinkedIn 第 3 步缺少预期的提交文字")
        elif step == 4 and not root.xpath('.//h3[contains(.,"application was sent")]'):
            raise ValueError("LinkedIn 第 4 步缺少样本中的历史提示")
    job.platform_specific_data.update(application_fields=prompts, apply_url=job.link,
                                      review_unverified=True)
    return job
