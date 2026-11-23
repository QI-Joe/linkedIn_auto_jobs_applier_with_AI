"""在私有目录内准备职位材料，使用实际排版验证可编辑 Word 陈述的页数。"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from docx import Document
from docx.shared import Cm, Pt


def write_json(path, record):
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(path):
    with path.open("rb") as stream:
        checksum = hashlib.sha256()
        for block in iter(lambda: stream.read(65536), b""):
            checksum.update(block)
    return checksum.hexdigest()


def check_resume(path):
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        output = subprocess.run(["pdfinfo", str(path.resolve())], capture_output=True, text=True,
                                env={**os.environ, "LC_ALL": "C"}, timeout=20)
        if output.returncode == 0 and re.search(r"(?m)^Pages:\s+[1-9]\d*\s*$", output.stdout):
            return
    if suffix == ".docx":
        try:
            with ZipFile(path) as document:
                if "word/document.xml" in document.namelist():
                    Document(path)
                    return
        except BadZipFile:
            pass
    raise ValueError("简历必须是可读取的 PDF 或 Word DOCX 文件")


def statement(directory, job, match, fact, office):
    doc = Document()
    section = doc.sections[0]
    section.page_height, section.page_width = Cm(29.7), Cm(21)
    section.left_margin = section.right_margin = Cm(2.5)
    style = doc.styles["Normal"]
    style.font.name, style.font.size = "Calibri", Pt(11)
    style.paragraph_format.space_after = Pt(10)
    doc.add_heading("Personal Statement", 0)
    doc.add_paragraph(f"{job.title}  |  {job.company}", style="Subtitle")
    opening = f"I am interested in the {job.title} position at {job.company}."
    if match["skills"]:
        focus = " and ".join(match["skills"][:2])
        opening += f" The opportunity to work on {focus} connects directly with my experience."
    doc.add_paragraph(opening)
    if match["requirements"]:
        # 只引用职位原文；按与已核实技能的交集选取最相关的要求。
        requirement = max(match["requirements"], key=lambda text:
                          sum(skill.casefold() in text.casefold() for skill in match["skills"]))
        doc.add_paragraph(f'One requirement that stands out to me is “{requirement.rstrip(".")}”.')

    doc.add_paragraph(f"One example from my background is {fact.context}. {fact.text.strip()}")
    closing = "I would welcome the opportunity to discuss this work and how I could contribute to your team."
    doc.add_paragraph(closing)
    word = directory / "Personal Statement.docx"
    doc.save(word)
    # 每次转换使用独立配置，避免并发时将任务转发到另一个 Writer 进程。
    with tempfile.TemporaryDirectory() as private:
        args = [office, "-env:UserInstallation=" + Path(private).as_uri(), "--headless",
                "--convert-to", "pdf", "--outdir", str(directory), str(word)]
        result = subprocess.run(args, capture_output=True, timeout=60)
        if result.returncode == 81:  # 部分发行版首次创建配置后要求重启一次
            result = subprocess.run(args, capture_output=True, timeout=60)
        pdf = word.with_suffix(".pdf")
        if result.returncode or not pdf.is_file():
            raise ValueError("Word 陈述导出失败，请检查 LibreOffice Writer 和字体")
    info = subprocess.check_output(["pdfinfo", str(pdf)], text=True, env={**os.environ, "LC_ALL": "C"}, timeout=20)
    if not re.search(r"(?m)^Pages:\s+1\s*$", info):
        raise ValueError("Personal Statement 超过一页，请缩短引用的 CV 经历后重新生成")
    content = subprocess.check_output(["pdftotext", str(pdf), "-"], text=True, timeout=20)
    if closing not in " ".join(content.split()):
        raise ValueError("PDF 末段不完整，请检查字体和页边距")
    return word


def prepare_version(output, day, job, match, fact, resume, cv_hash, office, review):
    job_id = job.get_platform_data("job_id")
    if not re.fullmatch(r"[0-9]+", job_id) or job.platform not in {"jobsdb", "linkedin"}:
        raise ValueError("无法建立安全且唯一的职位目录")
    parent = output / day.isoformat() / job.platform / job_id
    parent.mkdir(parents=True, exist_ok=True)
    # 完整生成后才发布版本；前次文件及原简历始终只读。
    with tempfile.TemporaryDirectory(dir=parent, prefix=".building-") as temporary:
        stage = Path(temporary) / "package"
        stage.mkdir(mode=0o700)
        copy = stage / ("Resume" + resume.suffix.lower())
        shutil.copyfile(resume, copy)
        check_resume(copy)
        word = statement(stage, job, match, fact, office)
        review_result = review({"resume": copy, "statement": word})
        version = "v-" + Path(temporary).name.removeprefix(".building-")
        suggested = [
            {"question": "Which experience is relevant to this role?", "answer": fact.text,
             "source": "cv:" + fact.source, "kind": "preparation_prompt"},
            {"question": "Are all requirements and application details confirmed?",
             "answer": None, "source": "needs_confirmation", "kind": "preparation_prompt"},
        ]
        write_json(stage / "answers.json", {"employer_questions": review_result["questions"],
                                            "suggested_questions": suggested})
        manifest = {"platform": job.platform, "job_id": job_id, "title": job.title, "company": job.company,
                    "location": job.location, "job_url": job.link, "apply_method": job.apply_method or "unknown",
                    "apply_url": job.get_platform_data("apply_url"), "version": version,
                    "day": day.isoformat(), "status": review_result["status"], "submitted": False,
                    "steps": review_result["steps"], "issues": review_result["issues"], "match": match,
                    "cv_sha256": cv_hash, "files": {p.name: digest(p) for p in sorted(stage.iterdir())}}
        write_json(stage / "manifest.json", manifest)
        stage.rename(parent / version)
    return parent / version
