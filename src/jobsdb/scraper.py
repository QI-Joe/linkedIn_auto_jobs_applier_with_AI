"""从 JobsDB 职位详情读取字段，调用方负责导航和申请决策。"""

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement


def read_detail_fields(sidebar: WebElement) -> dict[str, str]:
    """读取侧栏或独立详情页中的可见摘要；站点未披露的字段返回空串。"""
    selectors = {
        "title": 'h1[data-automation="job-detail-title"]',
        "company": '[data-automation="advertiser-name"]',
        "location": '[data-automation="job-detail-location"]',
        "description": '[data-automation="jobAdDetails"]',
        "work_style": '[data-automation="job-detail-work-type"]',
        "salary": '[data-automation="job-detail-salary"]',
    }
    fields = {}
    for name, selector in selectors.items():
        elements = sidebar.find_elements(By.CSS_SELECTOR, selector)
        fields[name] = elements[0].text.strip() if elements else ""
    return fields
