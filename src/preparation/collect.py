"""收集职位，与申请入口独立。浏览器只打开列表和同站职位详情。"""

from datetime import date
import json
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from lxml import html

from inspect_job_snapshot import inspect_snapshot, parse_listing
from src.jobsdb.preparation import parse_detail, read_detail
from src.linkedin.snapshot import public_detail, read_easy_apply_capture
from src.preparation.history import legacy_job


def import_log(history, path):
    # 早期日志既有数组，也有连续追加的 JSON 对象。
    raw = path.read_text(encoding="utf-8-sig").strip()
    decoder = json.JSONDecoder()
    idx = 0
    count = 0
    while idx < len(raw):
        value, idx = decoder.raw_decode(raw, idx)
        rows = value if isinstance(value, list) else [value]
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("旧日志包含非对象记录")
            job = legacy_job(row)
            if job:
                day = str(row.get("timestamp", ""))[:10] or path.name[:10]
                stamp = date.fromisoformat(day).isoformat() + "T00:00:00+00:00"
                history.save([job], "jobsdb-log", stamp)
                count += 1
        while idx < len(raw) and raw[idx].isspace():
            idx += 1
    return count


def platform_url(url):
    page = urlsplit(url)
    if page.scheme != "https" or page.netloc not in {"hk.jobsdb.com", "www.linkedin.com", "linkedin.com"}:
        raise ValueError("采集仅接受 JobsDB 香港站或 LinkedIn 的 HTTPS 页面")
    return page


def collect_page(history, driver, address, timeout=12):
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from selenium.webdriver.support.ui import WebDriverWait

    search = platform_url(address)
    driver.get(address)
    wait = WebDriverWait(driver, timeout)
    def listing(browser):
        current = platform_url(browser.current_url)
        if current.hostname != search.hostname:
            raise ValueError("职位列表跳转到不同主机")
        try:
            return parse_listing(browser.current_url, browser.page_source)
        except ValueError:
            return False

    cards = wait.until(listing, "未找到职位列表，请检查登录状态和页面结构")
    history.save(cards, "browser-list")
    seen = {j.get_platform_data("job_id") for j in cards}
    completed = 0
    for card in cards:
        job_id = card.get_platform_data("job_id")
        if not job_id.isdecimal():
            print(f"{card.platform} 卡片缺少平台 ID，已留档待确认")
            continue
        guest_card = card.get_platform_data("listing_layout") == "public"
        if card.platform == "jobsdb" or guest_card:
            detail_url = card.link
        else:
            query = parse_qs(search.query)
            query["currentJobId"] = [job_id]
            detail_url = urlunsplit(search._replace(query=urlencode(query, doseq=True)))

        def detail(browser):
            current = platform_url(browser.current_url)
            if current.hostname != search.hostname:
                raise ValueError("职位详情跳转到不同主机")
            if card.platform == "jobsdb":
                if current.path.rstrip("/") != f"/job/{job_id}":
                    return False
                root = html.fragment_fromstring(browser.page_source, create_parent="div")
                try:
                    found = parse_detail(root, job_id)
                except ValueError:
                    return False
            elif guest_card:
                root = html.fragment_fromstring(browser.page_source, create_parent="div")
                found = public_detail(root, browser.current_url, card)
            else:
                if parse_qs(current.query).get("currentJobId") != [job_id]:
                    return False
                jobs = listing(browser) or []
                # 动态列表可能在加载选中项时才渲染更多卡片，先归档，再依次补详情。
                additional = [j for j in jobs if j.get_platform_data("job_id") not in seen]
                if additional:
                    history.save(additional, "browser-list")
                    cards.extend(additional)
                    seen.update(j.get_platform_data("job_id") for j in additional)
                found = next((j for j in jobs if j.get_platform_data("job_id") == job_id), None)
            if not found or not found.description:
                return False
            if (card.title and card.title != found.title) or (card.company and card.company != found.company):
                return False
            return found

        try:
            driver.get(detail_url)
            history.save([wait.until(detail)], "browser-detail")
            completed += 1
        except (TimeoutException, WebDriverException, ValueError) as exc:
            print(f"{card.platform}/{job_id} 详情未确认，已保留卡片（{type(exc).__name__}）")
    return len(cards), completed


def collect(args, history):
    if not any((args.url, args.snapshot, args.detail, args.easy_apply_steps, args.legacy_log)):
        raise ValueError("请提供列表 URL、快照、JobsDB 详情或旧日志")
    for path in args.snapshot:
        jobs = inspect_snapshot(path)
        history.save(jobs, "snapshot-list")
        print(f"已读取 {len(jobs)} 张卡片")
    for path in args.detail:
        history.save([read_detail(path)], "snapshot-detail")
    if args.easy_apply_steps:
        history.save([read_easy_apply_capture(args.easy_apply_steps)], "snapshot-easy-apply")
    for path in args.legacy_log:
        files = sorted(path.glob("*_log.json")) if path.is_dir() else [path]
        if not files:
            raise ValueError("旧日志目录中没有 *_log.json")
        count = sum(import_log(history, entry) for entry in files)
        print(f"已读取 {len(files)} 份旧日志中的 {count} 条职位记录")
    if args.url:
        from selenium import webdriver
        for address in args.url:
            platform_url(address)
        options = webdriver.ChromeOptions()
        if args.browser_profile:
            options.add_argument("--user-data-dir=" + str(args.browser_profile.resolve()))
        with webdriver.Chrome(options=options) as driver:
            for address in args.url:
                count, full = collect_page(history, driver, address)
                print(f"已归档 {count} 张卡片，其中 {full} 条已核对详情")
    print(f"职位库：{history.path}")
