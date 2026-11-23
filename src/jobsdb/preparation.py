"""按 JobsDB 页面样本进行本地申请演练，只操作内存中的 HTML 树。"""

import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from lxml import html

from src.utils.job import Job


def page(path: Path):
    return html.fragment_fromstring(path.read_bytes().decode("utf-8"), create_parent="div",
                                    parser=html.HTMLParser(no_network=True))


def read_detail(path: Path) -> Job:
    raw = path.read_text(encoding="utf-8-sig")
    header, _, markup = raw.partition("\n")
    known_id = ""
    if header.strip().startswith("https://"):
        address = urlsplit(header.strip())
        match = re.fullmatch(r"/job/([0-9]+)/?", address.path)
        if address.netloc != "hk.jobsdb.com" or not match:
            raise ValueError("详情快照首行应为该 JobsDB 职位的 HTTPS 地址")
        known_id = match[1]
        raw = markup
    root = html.fragment_fromstring(raw, create_parent="div", parser=html.HTMLParser(no_network=True))
    return parse_detail(root, known_id)


def parse_detail(root, known_id=""):
    """没有站内申请按钮的详情也归档；ID 必须来自本平台职位地址。"""
    def field(name):
        return root.xpath('normalize-space(.//*[@data-automation=$name])', name=name)

    links = root.xpath('.//a[@data-automation="job-detail-apply"]')
    href = links[0].get("href", "") if len(links) == 1 else ""
    apply_url = urljoin("https://hk.jobsdb.com", href) if href else ""
    url = urlsplit(apply_url)
    native = re.fullmatch(r"/job/([0-9]+)/apply/?", url.path)
    native = native if (url.scheme, url.netloc) == ("https", "hk.jobsdb.com") else None
    ids = {known_id} if known_id else set()
    if native:
        ids.add(native[1])
    for canonical in root.xpath('.//link[@rel="canonical"]/@href'):
        address = urlsplit(canonical)
        match = re.fullmatch(r"/job/([0-9]+)/?", address.path)
        if match and address.hostname == "hk.jobsdb.com":
            ids.add(match[1])
    if len(ids) != 1:
        raise ValueError("JobsDB 详情缺少唯一的职位 ID")
    job_id = ids.pop()
    method = "Unknown"
    if native and field("job-detail-apply").casefold() == "quick apply":
        method = "Quick Apply"
    elif apply_url and url.hostname != "hk.jobsdb.com":
        method = "External"
    job = Job(field("job-detail-title"), field("advertiser-name"), field("job-detail-location"),
              f"https://hk.jobsdb.com/job/{job_id}", method, platform="jobsdb")
    job.description = field("jobAdDetails")
    job.industry = field("job-detail-classifications")
    job.salary = field("job-detail-salary")
    job.job_type = field("job-detail-work-type")
    if not all((job.title, job.company, job.description)):
        raise ValueError("详情页缺少标题、公司或正文")
    requirements = []
    for group in root.xpath('.//*[@data-automation="jobAdDetails"]//*[self::ul or self::ol]'):
        heading = group.xpath("normalize-space(preceding-sibling::*[1])").lower()
        if "looking for" in heading or "requirements" in heading:
            requirements.extend(item.text_content().strip() for item in group.xpath("./li"))
    job.platform_specific_data.update(job_id=job_id, requirements=requirements,
                                      apply_url=apply_url)
    return job


def question_label(control, form):
    """从最近的单题容器读取题干，避免跨题借用文字。"""
    if control.tag == "select" or control.get("type") not in {"radio", "checkbox"}:
        label = form.xpath('normalize-space(.//label[@for=$id])', id=control.get("id", ""))
        if label:
            return label
    for parent in control.iterancestors():
        if parent is form:
            break
        names_in_group = {el.get("name") for el in parent.xpath(".//input|.//select|.//textarea")}
        if names_in_group - {control.get("name")}:
            break
        labels = parent.xpath('.//*[self::strong or self::legend]')
        names = {el.text_content().strip() for el in labels if el.text_content().strip()}
        if len(names) == 1:
            return names.pop()
        if names:
            break
    return ""


def fill_questions(form, confirmed: dict) -> list[dict]:
    groups = defaultdict(list)
    for i, el in enumerate(form.xpath('.//input|.//select|.//textarea|.//*[@role="combobox" or @role="textbox" or @role="checkbox" or @role="radio"]')):
        if el.get("type") in {"hidden", "button", "submit"}:
            continue
        key = el.get("name") or f"unknown-{i}"
        groups[key].append(el)
    answers = []
    for key, controls in groups.items():
        first = controls[0]
        kind = first.get("type", "text") if first.tag == "input" else first.tag
        question = question_label(first, form)
        choices = {}
        if kind == "select":
            for opt in first.xpath(".//option[@value and @value!='']"):
                choices[opt.text_content().strip()] = opt
        if kind in {"radio", "checkbox"}:
            for el in controls:
                label = form.xpath("normalize-space(.//label[@for=$id])", id=el.get("id", ""))
                if label:
                    choices[label] = el
        record = {"field": key, "question": question, "type": kind, "options": list(choices),
                  "answer": None, "source": "needs_confirmation"}
        value = confirmed.get(question)
        if isinstance(value, dict):
            record["fact_key"] = value["fact"]
            value = value["value"]
        values = value if isinstance(value, list) else [value]
        valid = bool(question and values) and all(isinstance(v, str) and v.strip() for v in values)
        if kind != "checkbox" and len(values) != 1:
            valid = False
        if choices and (not valid or any(v not in choices for v in values)):
            valid = False
        if kind in {"radio", "checkbox", "select"} and not choices:
            valid = False
        if kind in {"checkbox", "radio"} and len(choices) != len(controls):
            valid = False
        if kind == "checkbox" and len(values) > 1 and any(
                str(v).casefold() in {"none of these", "none of the above"} for v in values):
            valid = False
        if kind not in {"radio", "checkbox", "select", "text", "textarea"}:
            valid = False
        if len(controls) > 1 and kind not in {"radio", "checkbox"}:
            valid = False
        if valid:
            # 丢弃快照原有的选中态。只在当前内存 DOM 写入经过用户确认的答案。
            for el in (first.xpath(".//option") if kind == "select" else controls):
                for attr in ("checked", "selected", "aria-checked"):
                    el.attrib.pop(attr, None)
            if kind in {"radio", "checkbox", "select"}:
                attr = "selected" if kind == "select" else "checked"
                for v in values:
                    choices[v].set(attr, attr)
                written = [label for label, el in choices.items() if attr in el.attrib]
                valid = set(written) == set(values)
            elif kind == "textarea":
                first.text = values[0]
            else:
                first.set("value", values[0])
            if valid:
                record.update(answer=value, source="confirmed_profile")
        answers.append(record)
    return answers


def rehearse(job, steps, confirmed, attachments):
    """按实际页面标记推进；返回到达的步骤、题目及需要人工处理的问题。"""
    result = {"status": "needs_confirmation", "steps": [], "questions": [], "issues": [],
              "submitted": False}
    for number in range(1, 5):
        matches = list(steps.glob(f"*step{number}.md"))
        if len(matches) != 1:
            result["issues"].append(f"第 {number} 步样本缺失或不唯一")
            break
        root = page(matches[0])
        title = root.xpath("normalize-space(.//h1)")
        company = root.xpath('normalize-space(.//h1/following-sibling::*[1])')
        if len(root.xpath(".//h1")) != 1 or (title, company) != (job.title, job.company):
            result["issues"].append(f"第 {number} 步的职位或公司无法与详情关联")
            break
        result["steps"].append(number)
        if number < 4 and not root.xpath('.//button[@data-testid="continue-button"]'):
            result["issues"].append(f"第 {number} 步缺少继续按钮")
        if number == 1:
            for name, testid in [("resume", "resumeFileInput"), ("statement", "coverLetterFileInput")]:
                inputs = root.xpath('.//*[@data-testid=$key]//input[@type="file"]', key=testid)
                path = attachments[name]
                if len(inputs) != 1 or not path.is_file() or not path.stat().st_size:
                    result["issues"].append(f"缺少 {name} 文件或上传字段")
                else:
                    accepts = inputs[0].get("accept", "").lower().split(",")
                    mime = {".pdf": "application/pdf", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}.get(path.suffix.lower())
                    if mime not in accepts and path.suffix.lower() not in accepts:
                        result["issues"].append(f"页面不接受 {name} 的文件类型")
        elif number == 2:
            forms = root.xpath(".//form")
            if len(forms) == 1:
                result["questions"] = fill_questions(forms[0], confirmed)
            if not result["questions"]:
                result["issues"].append("未识别到雇主题块，需人工核查")
            for q in result["questions"]:
                if q["source"] == "needs_confirmation":
                    result["issues"].append(q["question"] or f"无法识别控件 {q['field']}")
        elif number == 3:
            if not root.xpath('.//*[@data-automation="add-role"]'):
                result["issues"].append("无法识别更新资料页")
        else:
            if not root.xpath('.//*[@data-testid="review-role-req"]') or not root.xpath('.//button[@data-testid="review-submit-application"]'):
                result["issues"].append("无法识别雇主答案摘要或最终审阅按钮")
            if root.xpath('.//*[@data-testid="cover-letter-dont"]'):
                result["issues"].append("捕获的审阅页显示未附求职信；真实附件回显需重新核对")
            else:
                result["issues"].append("当前样本未建立陈述附件回显与本地版本的关联")
            resume_name = root.xpath('normalize-space(.//*[@data-testid="resume-upload"])')
            if resume_name != attachments["resume"].name:
                result["issues"].append("审阅页的简历回显与本次准备的简历文件不一致")
            if root.xpath('.//*[@data-automation="text-answered"]'):
                result["issues"].append("审阅页仅有问题摘要，逐项答案和服务端上传结果仍需人工核对")
        if result["issues"]:
            break
    return result
